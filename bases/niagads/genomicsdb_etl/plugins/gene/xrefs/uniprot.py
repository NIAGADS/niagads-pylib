"""
UniProt KB ID XRef Loader Plugin

Loads gene and protein cross-references from UniProt KB ID mapping files into the gene.xref
tables, filtering for Ensembl gene/protein IDs and mapping them to genes/proteins
by Ensembl stable ID.

Input file format:
    H0YM94         Ensembl    ENSG00000022976.16
    R4GNG1         Ensembl    ENSG00000111653.20
    R4GNG1         Ensembl_TRS ENST00000467678.5
"""

import re
from typing import Any, Dict, Iterator, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.structure import GeneModel
from niagads.database.genomicsdb.schema.gene.xrefs import (
    GeneXRef,
    ProteinXRef,
    XRefCategory,
)
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
    ResumeCheckpoint,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.utils.sys import read_open_ctx
from pydantic import BaseModel, Field

# Pattern to strip version suffix from Ensembl Gene IDs
ENSEMBL_GENE_VERSION_PATTERN = re.compile(r"^(ENSG*\d+)\.\d+$")
ENSEMBL_PROTEIN_VERSION_PATTERN = re.compile(r"^(ENSP*\d+)\.\d+$")


class UniProtXRefEntry(BaseModel):
    """Parsed UniProt entry with mapped Ensembl ID."""

    uniprot_id: str
    ensembl_id: str

    def __str__(self):
        return f"{self.uniprot_id}|{self.ensembl_id}"


class UniProtKBIDLoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """Parameters for UniProt KB ID Loader plugin."""

    file: str = Field(
        ...,
        description="Full path to UniProt KB ID mapping file (tab-delimited)",
    )

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="1.0",
    description=(
        "ETL Plugin to load gene and protein cross-references from UniProt KB ID (full) mapping file "
        f"into {GeneXRef.table_name()}."
    ),
    affected_tables=[GeneXRef, ProteinXRef],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=UniProtKBIDLoaderParams,
)


@PluginRegistry.register(metadata)
class UniProtKBIDLoader(AbstractBasePlugin):
    """
    ETL plugin for loading UniProt KB ID cross-references into the gene.xref table.

    Extracts Ensembl gene/transcript ID mappings from UniProt KB ID mapping files,
    strips version suffixes from Ensembl IDs, and creates xref records linking
    UniProt KB IDs to genes.
    """

    _params: UniProtKBIDLoaderParams  # type annotation

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self.__external_database: ExternalDatabase = None
        self.__gene_pk_ref: Dict[str, int] = {}
        # once you strip the .extension on the IDS, lots of duplicate mappings
        self.__seen: Dict[str, str] = {}
        self.__unmapped_genes: set[str] = set()

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    async def on_run_start(self, session):
        """Fetch and cache the UniProt external database record."""
        if self.is_etl_run:
            # Fetch UniProt external database reference using mixin
            self.__external_database = await self._params.fetch_xdbref(session)

            # going to have to pretty much match whole gene table, so cache it
            # to speed things up
            self.__gene_pk_ref = GeneModel.retrieve_gene_pk_mapping(session)
            self.logger.info(f"Cached {len(self.__gene_pk_ref)} gene_pk references.")

    @staticmethod
    def _strip_version_suffix(ensembl_id: str) -> str:
        """
        Strip the version suffix from an Ensembl ID.

        Examples:
            ENSG00000022976.16 -> ENSG00000022976
            ENST00000467678.5 -> ENST00000467678
            ENSG00000022976 -> ENSG00000022976 (already stripped)
        """
        match = ENSEMBL_GENE_VERSION_PATTERN.match(ensembl_id)
        if match:
            return match.group(1)
        return ensembl_id

    def extract(self) -> Iterator[UniProtXRefEntry]:
        """
        Extract UniProt KB ID entries from tab-delimited file.

        Filters for Ensembl ID types only and yields parsed entries.
        Expected format (tab-delimited):
            UniProtKB_ID  ID_Type  Mapped_ID
            H0YM94        Ensembl  ENSG00000022976.16
        """
        filtered_count = 0
        duplicate_count = 0

        with read_open_ctx(self._params.file) as fh:
            for line_number, line in enumerate(fh, start=1):
                uniprot_id, id_type, mapped_id = line.strip().split("\t")

                # Filter for Ensembl IDs only
                if id_type != "Ensembl":
                    filtered_count += 1
                    continue

                # Strip version suffix from Ensembl ID
                ensembl_id = self._strip_version_suffix(mapped_id)

                xref = UniProtXRefEntry(
                    uniprot_id=uniprot_id,
                    ensembl_id=ensembl_id,
                )

                # need to cache uniprot/ensembl pairs (uniprot can map to multiple genes)
                # to weed out duplicates
                if str(xref) in self.__seen:
                    self.logger.info(str(xref))
                    duplicate_count += 1
                    continue

                self.__seen[str(xref)] = 1

                if self._verbose and line_number % 5000 == 0:
                    self.logger.info(f"Parsed {line_number} total records")

                yield xref

        self.logger.info(f"Parsed {line_number} total records")
        if filtered_count > 0:
            self.logger.info(f"Filtered {filtered_count} non-Ensembl records")
        if duplicate_count > 0:
            self.logger.info(f"Skipped {filtered_count} duplicate records")
        self.logger.info(
            f"Extracted {line_number - filtered_count - duplicate_count} Ensembl records"
        )

    def transform(self, entry: UniProtXRefEntry) -> UniProtXRefEntry:
        """
        Transform a UniProt entry (minimal transformation for this simple format).

        Returns the entry as-is since it's already in the required format.
        """
        return entry

    async def load(self, session, mappings: list[UniProtXRefEntry]) -> ResumeCheckpoint:
        """
        Load a UniProt xref entry into the gene.xref table.
        """
        xrefs = []
        for entry in mappings:
            # Lookup the gene using Ensembl ID
            # gene_pk = await self.__lookup_gene(session, entry.ensembl_id)
            try:
                gene_pk = self.__gene_pk_ref[entry.ensembl_id]
            except:
                self.__unmapped_genes.add(entry.ensembl_id)
                self.inc_tx_count(GeneXRef, ETLOperation.SKIP)
                continue

            xrefs.append(
                GeneXRef(
                    gene_id=gene_pk,
                    xref_category=XRefCategory.IDENTIFIER,
                    xref_label="uniprot_id",
                    xref_value=entry.uniprot_id,
                    source_id=entry.uniprot_id,
                    external_database_id=self.external_database_id,
                    run_id=self.run_id,
                )
            )

        await GeneXRef.submit_many(session, xrefs)
        return self.create_checkpoint(record=mappings[-1])

    async def on_run_complete(self):
        """Log summary of unmapped genes."""
        num_skipped = len(self.__unmapped_genes)
        if num_skipped > 0:
            self.logger.warning(
                f"Skipped {num_skipped} unmapped genes. Likely deprecated or non-primary assembly."
            )
            self.logger.debug(f"Unmapped genes: {sorted(self.__unmapped_genes)}")

    def get_record_id(self, record: UniProtXRefEntry) -> str:
        """Return a unique identifier for the record."""
        return f"{record.uniprot_id}|{record.ensembl_id}"
