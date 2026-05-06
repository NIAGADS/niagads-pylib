"""
HGNC Gene Nomenclature XRef Loader Plugin

Loads gene cross-references from the HGNC (HUGO Gene Nomenclature Committee) JSON download file
into the gene.xref table, mapping genes by their Ensembl gene ID (stable_id/source_id).
"""

import json
from typing import Any, Dict, Iterator, List, Optional

from niagads.database.genomicsdb.schema.gene.structure import GeneModel
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.documents import Gene
from niagads.database.genomicsdb.schema.gene.xrefs import (
    GeneIdentifierType,
    GeneXRef,
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
from niagads.exceptions.core import ValidationError
from niagads.genomicsdb_etl.plugins.gene.xrefs.mappings import HGNC_XREF_CATEGORY_MAP
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.utils.string import dict_to_info_string, xstr
from niagads.utils.sys import read_open_ctx
from pydantic import BaseModel, Field

INVALID_XREFS = ["status", "uuid", "location_sortable", "curator_notes"]


class GeneXRefEntry(BaseModel):
    """Parsed HGNC entry with mapped xref category."""

    source_id: str
    ensembl_id: str
    xref_label: str  # the HGNC field name (e.g., "entrez_id", "omim_id")
    xref_value: str  # the field value
    xref_category: XRefCategory


class HGNCXRefLoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """Parameters for HGNC XRef Loader plugin."""

    file: str = Field(
        ...,
        description="Full path to HGNC JSON file",
    )
    verify_xref_keys: Optional[bool] = Field(
        default=False,
        description=(
            "verify xrefs against xref mapping, reporting any novel mappings; "
            "must set `--mode DRY_RUN`"
        ),
    )

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="1.0",
    description=(
        "ETL Plugin to load gene cross-references from HGNC JSON download file "
        f"into {GeneXRef.table_name()}. Maps genes by Ensembl gene ID (source_id) "
        "and creates xref records for all mapped HGNC identifiers and attributes."
    ),
    affected_tables=[GeneXRef],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=HGNCXRefLoaderParams,
)


@PluginRegistry.register(metadata)
class HGNCXRefLoader(AbstractBasePlugin):
    """
    ETL plugin for loading HGNC gene cross-references into the gene.xref table.

    Maps genes by Ensembl gene ID and creates xref records for all available HGNC
    identifiers and attributes according to HGNC_XREF_CATEGORY_MAP.
    """

    _params: HGNCXRefLoaderParams  # type annotation

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
        self.__unmapped_genes: set[str] = set()

        if self._params.verify_xref_keys and not self.is_dry_run:
            raise ValidationError("To verify XRef keys, set --mode DRY_RUN")

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    async def on_run_start(self, session):
        """Fetch and cache the HGNC external database record."""
        if self.is_etl_run:
            # Fetch HGNC external database reference using mixin
            self.__external_database = await self._params.fetch_xdbref(session)

            # going to have to pretty much match whole gene table, so cache it
            # to speed things up
            self.__gene_pk_ref = GeneModel.fetch_ensembl_to_pk_map(session)

            self.logger.info(f"Cached {len(self.__gene_pk_ref)} gene_pk references.")

    def extract(self) -> Iterator[dict]:
        """
        Extract HGNC records from JSON file.

        The HGNC JSON download file has the structure:
        { "response": { "docs": [...] }, ... }

        Yields each HGNC document (gene record).
        """
        invalid_ensembl_gene_count = 0
        valid_ensembl_gene_count = 0
        try:
            with read_open_ctx(self._params.file) as fh:
                data = json.load(fh)

            entries = data["response"]["docs"]
            self.logger.info(f"Read {len(entries)} HGNC records")

            for entry in entries:
                ensembl_id = entry.get("ensembl_gene_id", None)
                if ensembl_id is None:
                    invalid_ensembl_gene_count += 1
                else:
                    valid_ensembl_gene_count += 1
                    yield entry

            self.logger.info(f"Extracted {valid_ensembl_gene_count} Ensembl Genes")
            if invalid_ensembl_gene_count > 0:
                self.logger.info(f"Skipped {invalid_ensembl_gene_count} Ensembl Genes")

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse HGNC JSON file: {e}")

    def __is_empty_value(self, value):
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == "":
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        if isinstance(value, dict) and len(value) == 0:
            return True
        return False

    def __is_valid_xref(self, key: str, value):
        if self.__is_empty_value(value):
            return False
        if key.startswith("date_"):
            return False
        if key in INVALID_XREFS:
            return False
        return True

    def __format_xref_value(self, value):
        if isinstance(value, str):
            return value
        else:
            return xstr(value)

    def transform(self, entry: dict) -> List[GeneXRefEntry]:
        """
        Transform an HGNC record into a list of xref entries.

        For each field in the HGNC record that is mapped in HGNC_XREF_CATEGORY_MAP,
        create an HGNCGeneXRefEntry with the xref category.
        """

        ensembl_id = entry.get("ensembl_gene_id", None)
        hgnc_id = entry.get("hgnc_id")

        xrefs = []

        key: str
        for key, xref_value in entry.items():
            if not self.__is_valid_xref(key, xref_value):
                continue

            xref_label = key.replace(".", "_").replace("-", "_")
            try:
                category = HGNC_XREF_CATEGORY_MAP[xref_label]
            except KeyError as err:
                if self._params.verify_xref_keys:
                    self.logger.warning(f"Invalid xref: {key}")
                else:
                    raise err

            xref_label = key.replace("_ids", "_id")

            if isinstance(xref_value, list):
                for v in xref_value:
                    v_str = self.__format_xref_value(v)
                    xrefs.append(
                        GeneXRefEntry(
                            source_id=hgnc_id,
                            ensembl_id=ensembl_id,
                            xref_label=xref_label,
                            xref_value=v_str,
                            xref_category=str(category),
                        )
                    )
            else:
                v_str = self.__format_xref_value(xref_value)
                xrefs.append(
                    GeneXRefEntry(
                        source_id=hgnc_id,
                        ensembl_id=ensembl_id,
                        xref_label=xref_label,
                        xref_value=v_str,
                        xref_category=category,
                    )
                )

        return xrefs

    async def load(self, session, entries: List[GeneXRefEntry]) -> ResumeCheckpoint:
        """
        Load xref entries into the gene.xref table.
        """
        xrefs: List[GeneXRef] = []
        current_ensembl_id = None
        current_gene_pk = None
        gene_xref_count = 0
        for entry in entries:
            if current_ensembl_id != entry.ensembl_id:
                if self._verbose and current_ensembl_id is not None:
                    self.logger.debug(
                        f"Inserted {gene_xref_count} for {current_ensembl_id}:{current_gene_pk}"
                    )
                current_ensembl_id = entry.ensembl_id
                gene_xref_count = 0

                try:
                    current_gene_pk = self.__gene_pk_ref[current_ensembl_id]
                except:
                    self.__unmapped_genes.add(current_ensembl_id)
                    current_gene_pk = None

            if current_gene_pk is None:
                self.inc_tx_count(GeneXRef, ETLOperation.SKIP)
                continue

            xrefs.append(
                GeneXRef(
                    gene_id=current_gene_pk,
                    xref_category=entry.xref_category,
                    xref_label=entry.xref_label,
                    xref_value=entry.xref_value,
                    source_id=entry.source_id,
                    external_database_id=self.external_database_id,
                    run_id=self.run_id,
                )
            )
            gene_xref_count += 1

        await GeneXRef.submit_many(session, xrefs)
        return self.create_checkpoint(record=entries[-1])

    async def on_run_complete(self):
        num_skipped = len(self.__unmapped_genes)
        self.logger.warning(
            f"Skipped {num_skipped} unmapped genes. Likely deprecated or non-primary assembly."
        )
        self.logger.info(self.__unmapped_genes)

    def get_record_id(self, record: GeneXRefEntry) -> str:
        return f"{record.ensembl_id}|{record.source_id}"
