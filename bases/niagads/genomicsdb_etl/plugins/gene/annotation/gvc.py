"""
ADSP GVC Top Genes Loader Plugin

Loads ADSP Genome Variant Catalog (GVC) top genes into GeneListEntry and
AnnotationEvidence tables, with optional ranking and scoring information.
"""

from re import split as split_regex
from typing import Any, Dict, Optional

from niagads.common.models.annotations import (
    AnnotationEvidenceQualifier,
    AnnotationType,
)
from niagads.common.models.base import CustomBaseModel
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
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.mixins import ExternalDatabaseContextMixin
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorParamMixin,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefParamMixin,
)
from pydantic import Field, model_validator

EVIDENCE_CODE_CURIE = ""


class GVCEntry(CustomBaseModel):
    """Normalized representation of one ADSP GVC CSV row."""

    id: int
    reported_loci: list[str]
    grouped_loci: list[str]
    phase: str
    evaluation_criteria: Optional[str] = None
    population: list[str]
    phenotypes: list[str]
    study: str
    tier: int
    nearby_genes_500kb: list[str]
    agora_target: str

    @classmethod
    def from_parsed_line(cls, line: dict[str, Any]) -> "GVCEntry":
        """Create a normalized entry from one CSV parser result."""
        analysis = cls._split_value(line["Phase_1_or_2__VS_or_SV"])

        return cls(
            id=int(line["id"]),
            reported_loci=cls._split_gene_symbols(line["Reportedloci"]),
            grouped_loci=cls._split_value(line["Grouped_loci"], delimiter="/"),
            phase=analysis[0],
            evaluation_criteria=analysis[1] if len(analysis) > 1 else None,
            population=cls._split_value(
                line["Population"].replace(", and ", ", ")
            ),
            phenotypes=cls._split_value(line["Phenotypes"], delimiter="+"),
            study=line["Study"].strip(),
            tier=int(line["Tier"]),
            nearby_genes_500kb=cls._split_value(
                line["Nearby_genes_500kb__based_on_grouped_loci"]
            ),
            agora_target=line["AGORA_target_YN"].strip(),
        )

    @staticmethod
    def _split_value(value: Optional[str], delimiter: str = ",") -> list[str]:
        """Split a source value on one delimiter."""
        if value is None or not value.strip() or value.strip().upper() == "NA":
            return []

        return [
            item.strip().removeprefix("and ")
            for item in value.strip().split(delimiter)
        ]

    @staticmethod
    def _split_gene_symbols(value: Optional[str]) -> list[str]:
        """Split reported loci on the gene-list delimiters used by the source."""
        if value is None or not value.strip() or value.strip().upper() == "NA":
            return []

        return [item.strip() for item in split_regex(r"[/,;]", value) if item.strip()]


class CuratedLocusEvidenceQualifier(AnnotationEvidenceQualifier):
    reference_accession: str = "ADSP Gene Verification Committee (GVC)"
    description: str
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
    tier_description: str

    @model_validator(mode="after")
    def validate_tier_and_set_description(self):
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
        self.tier_description = TIER_DESCRIPTIONS[self.tier]
        if self.tier >= 3:
            self.description = f"Gene associated with a potential AD-associated Locus (ADSP GVC): {self.tier_description}"
        else:
            self.description = f"Gene associated with a known AD GWAS locus(ADSP GVC): {self.tier_description}"
        return self


class GVCGenesLoaderParams(
    BasePluginParams, PathValidatorParamMixin, ExternalDatabaseRefParamMixin
):
    """Parameters for ADSP GVC top genes loader plugin."""

    file: str = Field(..., description="full path to ADSP GVC top genes input file")

    validate_file_exists = PathValidatorParamMixin.validator("file")


metadata = PluginMetadata(
    version="0.1.0",
    description=(
        "ETL Plugin to load ADSP GVC top genes into "
        f"{GeneListEntry.table_name()} and (FUTURE) {AnnotationEvidence.table_name()} tables. "
        "Creates gene list entries with optional ranking and scoring, and (FUTURE) associated annotation evidence."
    ),
    affected_tables=[AnnotationEvidence, GeneListEntry],
    load_strategy=ETLLoadStrategy.BULK,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=GVCGenesLoaderParams,
)


@PluginRegistry.register(metadata)
class GVCGenesLoader(AbstractBasePlugin, ExternalDatabaseContextMixin):
    """
    ETL plugin to load ADSP GVC top genes into GeneListEntry and AnnotationEvidence tables.

    Processes input file containing top genes, creates gene list entries with optional
    score/rank, and creates corresponding annotation evidence records.
    """

    _params: GVCGenesLoaderParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)

        self._evidence_code_id: int = None
        self._table_ref: TableRef = None
        self._gene_pk_ref: dict = None

    async def on_run_start(self, session):
        """Validate xdbrefs and initialize database lookups."""
        await ExternalDatabaseContextMixin.on_run_start(self, session)
        if self.is_etl_run:
            # TODO: Get evidence code ontology_term_id
            self._evidence_code_id = await OntologyTerm.find_primary_key(
                session, curie=EVIDENCE_CODE_CURIE
            )

            self._gene_pk_ref = await GeneXRef.retrieve_gene_pk_mapping(
                session, gene_identifier_type=GeneIdentifierType.ENSEMBL
            )

            # Get table reference for GeneListEntry to use in AnnotationEvidence
            self._table_ref = await TableCatalog.get_table_ref(session, GeneListEntry)

            self.logger.info("Initialized ADSP GVC loader caches")

    def extract(self):
        parser = CSVFileParser(self._params.file)
        return parser.to_json()

    def __build_evidence_qualifier(self, entry: dict) -> CuratedLocusEvidenceQualifier:
        analysis = GVCEntry._split_value(entry["Phase_1_or_2__VS_or_SV"])
        tier = int(entry["Tier"])

        return CuratedLocusEvidenceQualifier(
            reported_loci=GVCEntry._split_gene_symbols(entry["Reportedloci"]),
            grouped_loci=GVCEntry._split_value(entry["Grouped_loci"], delimiter="/"),
            nearby_genes_500kb=GVCEntry._split_value(
                entry["Nearby_genes_500kb__based_on_grouped_loci"]
            ),
            phase=analysis[0],
            evaluation_criteria=analysis[1] if len(analysis) > 1 else None,
            population=entry["Population"].strip(),
            phenotypes=GVCEntry._split_value(entry["Phenotypes"], delimiter="+"),
            study=entry["Study"],
            tier=tier,
        )

    async def transform(self, records: list[dict]):
        pass

    async def load(self, transformed): ...

    def get_record_id(self, record) -> str: ...
