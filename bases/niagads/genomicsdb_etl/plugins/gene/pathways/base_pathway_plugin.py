from typing import List, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.database.genomicsdb.schema.gene.documents import Gene
from niagads.database.genomicsdb.schema.gene.xrefs import GeneIdentifierType
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.pathway import Pathway
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.genomicsdb_etl.plugins.gene.pathways.types import PathwayGeneAssociations
from pydantic import Field
from sqlalchemy.exc import NoResultFound


class PathwayMembershipLoaderPluginParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """
    Parameters for pathway-membership loading plugins
    """

    fail_on_missing_genes: bool = Field(default=False)


class PathwayMembershipLoaderPlugin(AbstractBasePlugin):
    """
    Loads KEGG pathway annotations from KGML XML files.
    """

    _params: PathwayMembershipLoaderPluginParams

    def __init__(
        self,
        params,
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self._external_database = None
        self._gene_pk_ref: dict = {}
        self._pathway_pk_ref: dict = {}
        self._seen_memberships: dict = {}
        self._unmapped_genes: set[str] = set()

    # --------- Properties

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    # --------- Base Plugin Overrides

    async def on_run_start(self, session):
        """on run start hook override"""

        # validate the xdbref against the database
        self.__external_database: ExternalDatabase = (
            await self._params.fetch_xdbref(session) if self.is_etl_run else None
        )

        self.logger.debug(
            f"external_database_id = {self.__external_database.external_database_id}"
        )

    def get_record_id(self, record: PathwayGeneAssociations):
        return f"{record.pathway_info.pathway_id}"

    # --------- Load Helpers

    async def _lookup_gene_primary_key(
        self, session, gene_id: str, gene_id_type: GeneIdentifierType
    ):
        """
        check for gene primary key in stored hash, if not found
        lookup in database; handle gene not found error.  Allow multiple genes found
        to propogate so plugin fails and issue can be investigated.
        """
        primary_key = self._gene_pk_ref.get(gene_id, None)
        if not primary_key:
            try:
                primary_key = await Gene.resolve_identifier(
                    session, id=gene_id, gene_identifier_type=gene_id_type
                )
            except NoResultFound:
                if self._params.fail_on_missing_genes:
                    self.logger.exception(f"Gene {gene_id} not found in database.")
                else:
                    # set placeholder primary key so we can detect, skip loading
                    # memberships, and avoid future lookups
                    self._unmapped_genes.add(gene_id)
                    primary_key = "NOT_FOUND"

            self._gene_pk_ref[gene_id] = primary_key

        return primary_key

    async def _retrieve_or_load_pathway(
        self, session, pathway_id: str, pathway_name: str
    ):
        """
        Check if a pathway exists or is already loaded. If it exists, return the primary key.
        Otherwise, load the pathway and return the new primary key.

        Args:
            session: The database session object.
            pathway_id (str): The identifier of the pathway.
            pathway_name (str): The name of the pathway.

        Returns:
            str: The primary key of the pathway.
        """

        primary_key = self._pathway_pk_ref.get(pathway_id, None)
        if primary_key is None:
            try:
                primary_key = await Pathway.find_primary_key(
                    session, filters={"source_id": pathway_id}
                )

            except NoResultFound:
                # load new pathway to database and
                # get new primary key
                pathway = Pathway(
                    source_id=pathway_id,
                    name=pathway_name,
                    external_database_id=self.external_database_id,
                    run_id=self.run_id,
                )
                primary_key = await pathway.submit(session)
            self._pathway_pk_ref[pathway_id] = primary_key

        return primary_key

    async def _load_pathway_membership(
        self,
        session,
        annotations: List[PathwayGeneAssociations],
        gene_id_type: GeneIdentifierType,
    ):
        """
        Helper function to load pathway data into the database.

        Args:
            session: The database session.
            annotations: List of pathway annotations (pathway_info, member_genes)
            gene_id_type: The type of gene identifier to use for resolving genes.
            is_multi_pathway_load (Optinal, book): flag indicating if all
        Returns:
            ResumeCheckpoint: The checkpoint for resuming the ETL process.
        """
        self.logger.debug(f"Initiating batch load; n={len(annotations)} records.")

        for pathway in annotations:
            # Lookup / possibly load pathway and get its primary key
            pathway_pk = await self._retrieve_or_load_pathway(
                session,
                pathway.pathway_info.pathway_id,
                pathway.pathway_info.pathway_name,
            )

            memberships = []
            for gene in pathway.member_genes:
                gene_pk = await self._lookup_gene_primary_key(
                    session, gene.gene_id, gene_id_type
                )

                # skip records with bad genes, if flagged
                # not to fail on missing genes; failure is handled in the
                # gene lookup function
                if gene_pk == "NOT_FOUND":
                    self.inc_tx_count(PathwayMembership, ETLOperation.SKIP)
                    continue

                # build membership array
                memberships.append(
                    PathwayMembership(
                        gene_id=gene_pk,
                        pathway_id=pathway_pk,
                        run_id=self.run_id,
                        external_database_id=self.external_database_id,
                    )
                )

            # submit pathway-memberships in bulk
            await PathwayMembership.submit_many(session, memberships)

        # checkpoint is that last successful submit
        return self.create_checkpoint(record=annotations[-1])

    async def on_run_complete(self):
        num_skipped = len(self._unmapped_genes)
        self.logger.warning(
            f"Skipped {num_skipped} unmapped genes. Likely RefSeq only, provisional, or non-primary assembly."
        )
        self.logger.info(self._unmapped_genes)
