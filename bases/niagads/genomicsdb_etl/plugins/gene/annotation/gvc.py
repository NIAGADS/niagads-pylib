"""
ADSP GVC Top Genes Loader Plugin

Loads ADSP Genome Variant Catalog (GVC) top genes into GeneListEntry and
AnnotationEvidence tables, with optional ranking and scoring information.
"""

from re import split as split_regex
from re import sub as sub_regex
from typing import Any, Dict, Optional

from niagads.common.models.annotations import (
    AnnotationEvidenceQualifier,
    AnnotationType,
)
from niagads.common.models.base import CustomBaseModel, SerializationOptions
from niagads.common.types import ETLOperation
from niagads.common.variant.types import VariantClass
from niagads.csv_parser.core import CSVFileParser
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.admin.types import TableRef
from niagads.database.genomicsdb.schema.gene.annotation import (
    AnnotationEvidence,
    GeneListMembership,
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
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

EVIDENCE_CODE_CURIE = (
    "ECO:0007758"  # curator inference from journal publication used in manual assertion
)

INVALID_GENE_MAP = {"INPPD5": "INPP5D", "SSPL2A": "SPPL2A", "HEATR": "HEATR4"}


class GVCEntry(CustomBaseModel):
    """Normalized representation of one ADSP GVC CSV row."""

    id: int
    reported_locus: list[str]
    grouped_locus: list[str]
    curation_classification: Optional[str] = None
    population: list[str]
    phenotypes: list[str]
    study: Optional[str] = None
    tier: int

    @classmethod
    def from_parsed_line(cls, line: dict[str, Any]):
        """Create a normalized entry from one CSV parser result."""
        population = line["Population"]
        if population:
            population = population.replace(", and ", ", ")

        return cls(
            id=int(line["id"]),
            reported_locus=cls._split_gene_symbols(line["Reportedloci"]),
            grouped_locus=cls._split_gene_symbols(line["Grouped_loci"]),
            curation_classification=line["Phase_1_or_2__VS_or_SV"],
            population=cls._split_value(population),
            phenotypes=cls._split_value(line["Phenotypes"], delimiter="+"),
            study=line["Study"].strip() if line["Study"] is not None else None,
            tier=int(line["Tier"]),
        )

    @staticmethod
    def _split_value(value: Optional[str], delimiter: str = ",") -> list[str]:
        """Split a source value on one delimiter.

        Args:
            value: Source value to split. ``None``, blank, and ``NA`` values
                produce an empty list.
            delimiter: Single delimiter separating source values.

        Returns:
            A list of stripped source values.
        """
        if value is None or not value.strip() or value.strip().upper() == "NA":
            return []

        return [
            item.strip().removeprefix("and ") for item in value.strip().split(delimiter)
        ]

    @staticmethod
    def _split_gene_symbols(value: Optional[str]) -> list[str]:
        """Split reported loci into normalized gene symbols.

        Args:
            value: Source reported-loci value. ``None``, blank, and ``NA``
                values produce an empty list.

        Returns:
            A list of gene symbols split on ``/``, ``,`` and ``;``. Parenthetical
            expressions attached to symbols are removed before returning them.
        """
        if value is None or not value.strip() or value.strip().upper() == "NA":
            return []

        symbols = split_regex(r"[/,;]", value)
        return [
            symbol
            for item in symbols
            if (symbol := sub_regex(r"\([^)]*\)", "", item).strip())
        ]


class CuratedLocusEvidenceQualifier(AnnotationEvidenceQualifier):
    data_source: str = "ADSP Gene Verification Committee (GVC): TopGenes"
    description: Optional[str] = None
    annotation_type: AnnotationType = AnnotationType.DB

    study: Optional[str] = None
    population: Optional[list[str]] = None  # FIXME: ontology term
    phenotypes: Optional[list[str]] = None  # FIXME: should be ontology terms

    reported_locus: str
    grouped_locus: str

    curation_classification: str

    tier: int
    tier_description: Optional[str] = None

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


class GeneAnnotationRecord(CustomBaseModel):
    gene_symbol: str
    evidence: CuratedLocusEvidenceQualifier


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
        f"{GeneListMembership.table_name()} and (FUTURE) {AnnotationEvidence.table_name()} tables. "
        "Creates gene list entries with optional ranking and scoring, and (FUTURE) associated annotation evidence."
    ),
    affected_tables=[AnnotationEvidence, GeneListMembership],
    load_strategy=ETLLoadStrategy.CHUNKED,
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
        self._gene_membership_ref = {}
        self._unmapped_genes = {}

    async def on_run_start(self, session):
        """Validate xdbrefs and initialize database lookups."""
        await ExternalDatabaseContextMixin.on_run_start(self, session)
        if self.is_etl_run:
            # TODO: Get evidence code ontology_term_id
            self._evidence_code_id = await OntologyTerm.find_primary_key(
                session, curie=EVIDENCE_CODE_CURIE
            )

            self._gene_pk_ref = await GeneXRef.retrieve_gene_pk_mapping(
                session, gene_identifier_type=GeneIdentifierType.SYMBOL
            )

            # Get table reference for GeneListEntry to use in AnnotationEvidence
            self._table_ref = await TableCatalog.get_table_ref(
                session, GeneListMembership
            )

            self.logger.info("Initialized ADSP GVC loader caches")

    def extract(self):
        parser = CSVFileParser(self._params.file)
        contents = parser.to_json()
        for line in contents:
            yield GVCEntry.from_parsed_line(line)

    def __build_evidence_qualifier(
        self, entry: GVCEntry
    ) -> CuratedLocusEvidenceQualifier:

        try:
            return CuratedLocusEvidenceQualifier(
                reported_locus=", ".join(entry.reported_locus),
                grouped_locus=", ".join(entry.grouped_locus),
                curation_classification=entry.curation_classification,
                population=entry.population or None,
                phenotypes=entry.phenotypes or None,
                study=entry.study,
                tier=entry.tier,
            )
        except Exception as err:
            self.logger.debug(f"Unable to extract qualifiers: {entry.model_dump()}")
            raise err

    async def transform(self, entry: GVCEntry) -> list[GeneAnnotationRecord]:
        records = []
        # self.logger.debug(f"Entry: {entry.model_dump()}")
        for gene_symbol in entry.grouped_locus:
            records.append(
                GeneAnnotationRecord(
                    gene_symbol=gene_symbol,
                    evidence=self.__build_evidence_qualifier(entry),
                )
            )

        return records

    async def load(self, session, records: list[GeneAnnotationRecord]):
        evidence_records = []

        for record in records:
            gene_symbol = INVALID_GENE_MAP.get(record.gene_symbol, record.gene_symbol)
            gene_pk = self._gene_pk_ref.get(gene_symbol)

            if gene_pk is None:
                try:
                    gene_pk = await GeneXRef.resolve_symbol(
                        session,
                        gene_symbol,
                        match_synonyms=True,
                    )
                except NoResultFound:
                    self.logger.warning(f"Gene not found: {gene_symbol}")
                    self._unmapped_genes[gene_symbol] = (
                        f"{record.evidence.grouped_locus}//{record.evidence.reported_locus}"
                    )
                except MultipleResultsFound:
                    self.logger.warning(
                        f"Multiple genes found; unable to map: {gene_symbol}"
                    )
                    self._unmapped_genes[gene_symbol] = 1
            if gene_pk is None:
                self.inc_tx_count(GeneListMembership, ETLOperation.SKIP)
                continue

            # only want to load each gene/tier combination once
            # rest of details are in the evidence
            membership_key = (gene_symbol, record.evidence.tier)
            gene_membership_pk = self._gene_membership_ref.get(membership_key)

            if not gene_membership_pk:
                gene_membership_pk = await GeneListMembership(
                    gene_id=gene_pk,
                    rank=record.evidence.tier,
                    external_database_id=self.external_database_id,
                    run_id=self.run_id,
                ).submit(session)

                self._gene_membership_ref[membership_key] = gene_membership_pk

            # create the evidence
            evidence_records.append(
                AnnotationEvidence(
                    table_id=self._table_ref.table_id,
                    row_id=gene_membership_pk,
                    evidence_code_id=self._evidence_code_id,
                    qualifiers=record.evidence.model_dump(
                        exclude_none=True,
                        exclude_unset=True,
                        context={SerializationOptions.ENUMS_AS_VALUE: True},
                    ),
                    external_database_id=self.external_database_id,
                    run_id=self.run_id,
                )
            )

        await AnnotationEvidence.submit_many(session, evidence_records)

        return self.create_checkpoint(record=records[-1])

    def get_record_id(self, record: GeneAnnotationRecord) -> str:
        return record.gene_symbol

    async def on_run_complete(self):
        self.logger.debug(
            f"Unable to map {len(self._unmapped_genes)} genes: {self._unmapped_genes}"
        )
