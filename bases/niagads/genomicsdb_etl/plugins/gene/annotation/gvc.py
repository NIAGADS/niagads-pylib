"""
ADSP GVC Top Genes Loader Plugin

Loads ADSP Genome Variant Catalog (GVC) top genes into GeneListEntry and
AnnotationEvidence tables, with optional ranking and scoring information.
"""

from typing import Any, Dict, Optional

from niagads.common.models.annotations import (
    AnnotationEvidenceQualifier,
    AnnotationType,
)
from niagads.common.types import ETLOperation
from niagads.common.variant.types import VariantClass
from niagads.csv_parser.core import CSVFileParser
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.admin.types import TableRef
from niagads.database.genomicsdb.schema.gene.annotation import (
    AnnotationEvidence,
    GeneListEntry,
)
from niagads.database.genomicsdb.schema.gene.xrefs import GeneIdentifierType, GeneXRef
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from pydantic import Field


from typing import Literal
from pydantic import Field, model_validator


class CuratedLocusEvidenceQualifier(AnnotationEvidenceQualifier):
    annotation_type: AnnotationType = AnnotationType.DB

    study: str
    population: Optional[str] = None  # FIXME: ontology term
    phenotypes: list[str]  # FIXME: should be ontology terms

    reported_locus: str
    grouped_loci: Optional[list[str]] = None
    nearby_genes_500kb: list[str]

    phase: str
    evaluation_criteria: VariantClass

    tier: int
    tier_label: str
    tier_description: str

    @model_validator(mode="after")
    def validate_tier_and_set_label(self):
        TIER_DESCRIPTIONS = {
            1: "sufficient_evidence_of_association",
            2: "sufficient_evidence_with_missing_or_suboptimal_information",
            3: "suggestive_evidence_of_association",
            4: "suggestive_evidence_with_missing_or_suboptimal_information",
            5: "suggestive_evidence_single_dataset",
            6: "limited_evidence_of_association",
            7: "insufficient_evidence_of_association",
        }

        if self.tier < 1 or self.tier > 7:
            raise ValueError("tier must be between 1 and 7")
        self.tier_label = f"Tier {self.tier}"
        self.tier_description = TIER_DESCRIPTIONS[self.tier]
        return self


def clean_split(value: str, delimiter: str = ",") -> list[str]:
    clean_value = value.replace(", and", ", ")
    return [v.strip() for v in clean_value.split(delimiter)]


class AdspGvcTopGenesParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """Parameters for ADSP GVC top genes loader plugin."""

    file: str = Field(..., description="full path to ADSP GVC top genes input file")

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="0.1.0",
    description=(
        "ETL Plugin to load ADSP GVC top genes into "
        f"{GeneListEntry.table_name()} and {AnnotationEvidence.table_name()} tables. "
        "Creates gene list entries with optional ranking and scoring, and associated annotation evidence."
    ),
    affected_tables=[GeneListEntry, AnnotationEvidence],
    load_strategy=ETLLoadStrategy.BULK,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=AdspGvcTopGenesParams,
)


@PluginRegistry.register(metadata)
class AdspGvcTopGenesLoader(AbstractBasePlugin):
    """
    ETL plugin to load ADSP GVC top genes into GeneListEntry and AnnotationEvidence tables.

    Processes input file containing top genes, creates gene list entries with optional
    score/rank, and creates corresponding annotation evidence records.
    """

    _params: AdspGvcTopGenesParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)

        self.__external_database_id: int = None
        self.__evidence_code_id: int = None
        self.__gene_list_entry_table_ref: TableRef = None
        self.__gene_pk_ref: dict = None

    async def on_run_start(self, session):
        """Validate xdbrefs and initialize database lookups."""
        if self.is_etl_run:
            # Fetch ADSP GVC external database reference
            self.__external_database_id = (
                await self._params.fetch_xdbref(session)
            ).external_database_id

            # TODO: Get evidence code ontology_term_id
            # self.__evidence_code_id = ...

            self.__gene_pk_ref = await GeneXRef.retrieve_gene_pk_mapping(
                session, gene_identifier_type=GeneIdentifierType.ENSEMBL
            )

            # Get table reference for GeneListEntry to use in AnnotationEvidence
            self.__gene_list_entry_table_ref = await TableCatalog.get_table_ref(
                session, GeneListEntry
            )

            self.logger.info("Initialized ADSP GVC loader caches")

    def extract(self):
        parser = CSVFileParser(self._params.file)
        return parser.to_json()

    def __build_evidence_qualifier(self, entry: dict) -> CuratedLocusEvidenceQualifier:
        analysis = clean_split(entry["Phase_1_or_2__VS_or_SV"])
        tier = int(entry["Tier"])

        return CuratedLocusEvidenceQualifier(
            reported_loci=clean_split(entry["Reportedloci"]),
            grouped_loci=clean_split(entry["Grouped_loci"]),
            nearby_genes_500kb=clean_split(
                entry["Nearby_genes_500kb__based_on_grouped_loci"]
            ),
            phase=analysis[0],
            evaluation_criteria=analysis[1] if len(analysis == 2) else None,
            population=clean_split(entry["Population"]),
            phenotypes=clean_split(entry["Phenotypes"], delimiter="+"),
            study=entry["Study"],
            tier=tier,
        )

    async def transform(self, records: list[dict]): ...

    async def load(self, transformed): ...

    def get_record_id(self, record) -> str: ...
