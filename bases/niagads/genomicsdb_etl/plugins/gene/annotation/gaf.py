"""
GO Annotation File (GAF) Loader Plugin

Loads Gene Ontology (GO) annotations from GAF 2.2 format files into the
GOAssociation and AnnotationEvidence tables, mapping gene references through
GeneXRef.
"""

from typing import Any, Dict, Iterator, List, Optional

from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.admin.types import TableRef
from niagads.database.genomicsdb.schema.gene.annotation import (
    AnnotationEvidence,
    GOAssociation,
)
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.database.genomicsdb.schema.gene.xrefs import GeneIdentifierType, GeneXRef
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
    ResumeCheckpoint,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from niagads.utils.sys import read_open_ctx
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import NoResultFound


class GAFEntry(BaseModel):
    db: str  # database name
    db_object_id: str  # source id
    db_object_symbol: str  # Gene symbol
    qualifier: Optional[str] = None
    go_id: str  # GO term ID
    db_reference: Optional[str] = None  # GO_REF:000...
    evidence_code: str  # IBA, IEP, etc.
    with_or_from: Optional[List[str]] = None
    aspect: str  # F (function), C (component), P (process)
    db_object_name: Optional[str] = None
    db_object_synonym: Optional[str] = None
    db_object_type: Optional[str] = None
    taxon: Optional[str] = None
    date: Optional[str] = None
    assigned_by: Optional[str] = None
    annotation_extension: Optional[str] = None
    gene_product_form_id: Optional[str] = None

    @field_validator("with_or_from", mode="before")
    @classmethod
    def split_with_or_from(cls, v):
        if v is None:
            return None
        return [x for x in v.split("|")]


class GOAssociationEntry(BaseModel):
    uniprot_id: str
    term_curie: str
    evidence_code: str
    qualifiers: Optional[dict]


class GAFLoaderParams(BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin):
    """Parameters for GO Annotation File (GAF) loader plugin."""

    file: str = Field(..., description="Full path to GAF 2.2 file")

    go_xdbr: str = Field(
        ...,
        description="GO ontology external database reference (name|version) for "
        "mapping GO terms",
    )
    eco_xdbr: str = Field(
        ...,
        description="Evidence Code Ontology (ECO) external database reference "
        "(name|version) for mapping evidence codes",
    )

    validate_file_exists = PathValidatorMixin.validator("file")


# class GOAnnotationEntry(BaseModel):
#     """Processed GO annotation entry ready for database load."""

#     gene_id: int
#     go_term_id: int
#     evidence_code_id: int
#     db_reference: Optional[str] = None
#     with_or_from: Optional[list[str]] = None
#     qualifier: Optional[str] = None


metadata = PluginMetadata(
    version="1.0",
    description=(
        "ETL Plugin to load Gene Ontology (GO) annotations from GAF 2.2 files into "
        f"{GOAssociation.table_name()} and {AnnotationEvidence.table_name()}. "
        "Maps gene identifiers via UniProtKB"
    ),
    affected_tables=[AnnotationEvidence, GOAssociation],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.LOAD,
    is_large_dataset=False,
    parameter_model=GAFLoaderParams,
)


@PluginRegistry.register(metadata)
class GAFLoader(AbstractBasePlugin):
    """
    ETL plugin for loading GO annotations from GAF 2.2 files into the
    gene.goassociation and gene.annotationevidence tables.

    Handles:
    - Parsing GAF 2.2 format files
    - Mapping UniProt IDs to genes via GeneXRef
    - Mapping GO IDs to ontology terms
    - Mapping evidence codes to ECO terms
    - Creating annotation evidence records with qualifiers and references
    """

    _params: GAFLoaderParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)

        self.__go_xdbr_id: int = None
        self.__eco_xdbr_id: int = None
        self.__external_database_id: int = None
        self.__goa_table_ref: TableRef = None

        self.__gene_pk_ref: Dict[str, int] = {}
        self.__evidence_code_pk_ref: Dict[str, int] = {}
        self.__go_curie_pk_ref: Dict[str, int] = {}

        self.__unmapped_genes: set[str] = set()

    async def on_run_start(self, session):
        """Fetch and cache ontology references and build gene lookup cache."""
        if self.is_etl_run:
            # Fetch external database references for the GO annotations
            self.__external_database_id = (
                await self._params.fetch_xdbref(session)
            ).external_database_id

            # Gene Ontology external_database_id
            xdbref_param = ExternalDatabaseRefMixin(xdbref=self._params.go_xdbr)
            self.__go_xdbr_id: int = (
                await xdbref_param.fetch_xdbref(session)
            ).external_database_id

            # ECO external_database_id
            xdbref_param = ExternalDatabaseRefMixin(xdbref=self._params.eco_xdbr)
            self.__eco_xdbr_id: int = (
                await xdbref_param.fetch_xdbref(session)
            ).external_database_id

            # going to have to pretty much match whole gene table, so cache it
            # to speed things up
            self.__gene_pk_ref = GeneXRef.retrieve_gene_pk_mapping(
                session, gene_identifier_type=GeneIdentifierType.UNIPROT
            )

            # Get table reference for annotation evidence
            self.__goa_table_ref = await TableCatalog.get_table_ref(
                session, GOAssociation
            )

    def extract(self) -> Iterator[GAFEntry]:
        """Extract GO annotations from GAF file."""
        fields = list(GAFEntry.model_fields.keys())
        with read_open_ctx(self._params.file) as fh:
            for line in fh:
                if line.startswith("!"):
                    continue
                values = line.strip().split("\t")
                entry = dict(zip(fields, values))
                yield GAFEntry(**entry)

    def __lookup_gene_pk(self, uniprot_id: str) -> Optional[int]:
        """Look up gene ID by UniProt identifier."""
        # Check cache first
        try:
            return self.__gene_pk_ref[uniprot_id]
        except:
            self.__unmapped_genes.add(uniprot_id)
            return None

    def __build_qualifiers(self, entry: GAFEntry) -> dict:
        """Build qualifiers dict for AnnotationEvidence."""
        qualifiers = {}

        if entry.qualifier:
            qualifiers["qualifier"] = entry.qualifier

        if entry.db_reference:
            qualifiers["reference"] = entry.db_reference

        if entry.with_or_from:
            qualifiers["with_or_from"] = entry.with_or_from

        return qualifiers if qualifiers else None

    async def transform(self, entry: GAFEntry):
        """
        transform GAFEntry into a GOAssociationEntry
        """
        return GOAssociationEntry(
            entry.db_object_id,
            term_curie=entry.go_id,
            evidence_code=entry.evidence_code,
            qualifiers=self.__build_qualifiers(entry),
        )

    async def __lookup_evidence_code(self, session, code: str):
        """find ontology_term_id matching evidence code"""
        try:
            ontology_term_id = self.__evidence_code_pk_ref[code]
        except:
            try:  # look up in database
                ontology_term_id = await OntologyTerm.find_primary_key(
                    session,
                    term=code,
                    external_database_id=self.__eco_xdbr_id,
                )
                self.__evidence_code_pk_ref[code] = ontology_term_id
                self.logger.critical(f"Matched {code} - {ontology_term_id}")
            except:
                ontology_term_id = await OntologyTerm.find_primary_key(
                    session,
                    term=code,
                    external_database_id=self.__eco_xdbr_id,
                    search_synonyms=True,
                )
                self.__evidence_code_pk_ref[code] = ontology_term_id
                self.logger.critical(f"Matched {code} - {ontology_term_id}")

        return ontology_term_id

    async def __lookup_go_term_curie(self, session, curie: str):
        """find ontology_term_id matching evidence code"""
        try:
            ontology_term_id = self.__go_curie_pk_ref[curie]
        except:
            ontology_term_id = await OntologyTerm.find_primary_key(
                session,
                source_id=curie,
                external_database_id=self.__go_xdbr_id,
            )
            self.__go_curie_pk_ref[curie] = ontology_term_id
            self.logger.critical(f"Matched {curie} - {ontology_term_id}")

        return ontology_term_id

    async def load(
        self, session, entries: List[GOAssociationEntry]
    ) -> ResumeCheckpoint:
        """
        Load GO annotations into GOAssociation and AnnotationEvidence tables.

        Args:
            session: AsyncSession for database operations
            records: List of GOAssociationEntry objects to load

        Returns:
            ResumeCheckpoint for resumable runs
        """
        for entry in entries:
            # Lookup gene by UniProt ID
            gene_id = await self.__lookup_gene_pk(session, entry.uniprot_id)
            if gene_id is None:
                self.inc_tx_count(GOAssociation, ETLOperation.SKIP)
                continue

            # Lookup GO term
            term_ontology_term_id = self.__lookup_go_term_curie(
                session, entry.term_curie
            )

            # Lookup ECO code
            eco_term_id = self.__lookup_evidence_code(session, entry.evidence_code)

            # Create GOAssociation record
            association = GOAssociation(
                gene_id=gene_id,
                go_term_id=term_ontology_term_id,
                external_database_id=self.__external_database_id,
                run_id=self.run_id,
            )

            association_pk = association.submit(session)

            # LEFT OFF HERE
            annotation_evidences: List[AnnotationEvidence] = []
            for idx, go_assoc in enumerate(go_associations):
                eco_term_id, qualifiers = annotation_data[idx]
                annotation_ev = AnnotationEvidence(
                    evidence_code_id=eco_term_id,
                    table_id=self.__goa_table_ref.table_id,
                    row_id=go_assoc.go_association_id,
                    qualifiers=qualifiers,
                    run_id=self.run_id,
                )
                annotation_evidences.append(annotation_ev)

            if annotation_evidences:
                await AnnotationEvidence.submit_many(session, annotation_evidences)

        if entries:
            return self.create_checkpoint(record=entries[-1])
        return None

    def get_record_id(self, record: GAFEntry) -> str:
        """Return unique identifier for checkpoint."""
        return f"{record.db_object_id}|{record.go_id}"

    async def on_run_complete(self):
        """Log summary statistics after run completion."""
        total_unmapped_genes = len(self.__unmapped_genes)
        total_unmapped_go = len(self.__unmapped_go_terms)
        total_unmapped_eco = len(self.__unmapped_eco_codes)

        if self.__skipped_records > 0:
            self.logger.warning(
                f"Skipped {self.__skipped_records} records due to " f"mapping failures"
            )

        if total_unmapped_genes > 0:
            self.logger.warning(
                f"Could not map {total_unmapped_genes} UniProt identifiers to genes"
            )
            if self._verbose:
                self.logger.debug(f"Unmapped genes: {self.__unmapped_genes}")

        if total_unmapped_go > 0:
            self.logger.warning(
                f"Could not find {total_unmapped_go} GO term identifiers"
            )
            if self._verbose:
                self.logger.debug(f"Unmapped GO terms: {self.__unmapped_go_terms}")

        if total_unmapped_eco > 0:
            self.logger.warning(
                f"Could not find {total_unmapped_eco} ECO evidence codes"
            )
            if self._verbose:
                self.logger.debug(f"Unmapped ECO codes: {self.__unmapped_eco_codes}")
