import json
from copy import deepcopy
from typing import Any, Iterator, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, EmbeddingParameterMixin, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genome_reference.human import HumanGenome
from niagads.nlp.llm_types import LLM, NLPModelType
from pydantic import BaseModel, ConfigDict, Field, field_validator

CONSEQUENCE_ARRAYS = [
    "transcript_consequences",
    "motif_feature_consequences",
    "regulatory_feature_consequences",
    "intergenic_consequences",
]

SCORE_FIELDS = [
    "cadd_raw",
    "cadd_phred",
    "enformer_sad",
    "enformer_sar",
]

IMPACTED_GENE_FIELDS = [
    "gene_symbol",
    "gene_symbol_source",
    "hgnc_id",
    "biotype",
    "canonical",
    "appris",
    "mane",
    "mane_select",
    "protein_id",
    "ccds",
    "swissprot",
    "trembl",
    "tsl",
    "uniparc",
    "loftool",
]


class ImpactedGene(BaseModel):
    gene_id: str
    gene_symbol: Optional[str] = None
    loftool: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class VEPAnnotationExtractEntry(BaseModel):
    chrom: HumanGenome
    pos: int
    ref: str
    alt: str
    impacted_genes: Optional[list[ImpactedGene]] = None
    most_severe_consequence: Optional[dict[str, Any]] = None
    allele_frequency: Optional[dict[str, Any]] = None
    annotation: Optional[dict[str, list[dict[str, Any]]]] = None
    scores: Optional[dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class VEPAnnotationLoaderParams(BasePluginParams, PathValidatorMixin, EmbeddingParameterMixin):
    file: str = Field(description="Path to VEP JSON file")
    summarization_model: Optional[LLM] = Field(
        default=LLM.BART_LARGE_CNN, description="LLM model for generating textual summaries of the VEP annotation")
    validate_file_exists = PathValidatorMixin.validator("file")

    @field_validator("summarization_model")
    @classmethod
    def validate_embedding_model(cls, v: LLM) -> LLM:
        """Validate that summarization_model is in allowed summarization models list."""
        LLM.validate(v, NLPModelType.SUMMARIZATION)
        return LLM(v)


metadata = PluginMetadata(
    version="1.0",
    description=f"Update existing {Variant.table_name()} records with VEP annotation." "Includes translating to human readable text and calculating embeddings",
    affected_tables=[Variant],

    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.UPDATE,
    is_large_dataset=True,
    parameter_model=VEPAnnotationLoaderParams,
    can_resume=True,
)


@PluginRegistry.register(metadata=metadata)
class VEPAnnotationLoader(AbstractBasePlugin):
    _params: VEPAnnotationLoaderParams

    def __init__(self, params, name=None, log_path=None, debug=False, verbose=False):
        super().__init__(params, name, log_path, debug, verbose)

    async def on_run_start(self, session):
        # initialize embedding models
        ...

    def __get_annotated_alleles(
        self, annotation: dict[str, Any], input_alt_alleles: list[str]
    ) -> list[str]:
        alleles: list[str] = []
        for array_name in CONSEQUENCE_ARRAYS:
            for consequence in annotation.get(array_name, []):
                allele = consequence.get("variant_allele")
                if allele is None or allele in alleles:
                    continue
                alleles.append(allele)

        if input_alt_alleles:
            annotated_alt_alleles = [alt for alt in input_alt_alleles if alt in alleles]
            if annotated_alt_alleles:
                return annotated_alt_alleles

        return alleles

    def __filter_consequences_for_allele(
        self, annotation: dict[str, Any], alt_allele: str
    ) -> dict[str, list[dict[str, Any]]]:
        filtered = {}
        for array_name in CONSEQUENCE_ARRAYS:
            consequence_entries = []
            for consequence in annotation.get(array_name, []):
                if consequence.get("variant_allele") == alt_allele:
                    consequence_entries.append(deepcopy(consequence))
            if consequence_entries:
                filtered[array_name] = consequence_entries

        return filtered

    def __extract_scores(
        self, annotation: dict[str, list[dict[str, Any]]]
    ) -> Optional[dict[str, Any]]:
        scores = {}
        for consequences in annotation.values():
            for consequence in consequences:
                for score_field in SCORE_FIELDS:
                    if score_field in consequence and score_field not in scores:
                        scores[score_field] = consequence.pop(score_field)
                    else:
                        consequence.pop(score_field, None)

        return scores or None

    def __extract_impacted_genes(
        self, annotation: dict[str, list[dict[str, Any]]]
    ) -> Optional[list[ImpactedGene]]:
        impacted_genes = []
        seen_gene_ids = set()

        for consequences in annotation.values():
            for consequence in consequences:
                gene_id = consequence.get("gene_id")
                if gene_id is not None and gene_id not in seen_gene_ids:
                    impacted_genes.append(
                        ImpactedGene(
                            gene_id=gene_id,
                            gene_symbol=consequence.get("gene_symbol"),
                            loftool=consequence.get("loftool"),
                        )
                    )
                    seen_gene_ids.add(gene_id)

                for field in IMPACTED_GENE_FIELDS:
                    consequence.pop(field, None)

        return impacted_genes or None

    def __get_most_severe_consequence(
        self, annotation: dict[str, list[dict[str, Any]]], most_severe_term: Optional[str]
    ) -> Optional[dict[str, Any]]:
        if most_severe_term is None:
            return None

        for array_name in CONSEQUENCE_ARRAYS:
            for consequence in annotation.get(array_name, []):
                if most_severe_term in consequence.get("consequence_terms", []):
                    return deepcopy(consequence)

        return None

    def __extract_allele_frequency(
        self, annotation: dict[str, Any], alt_allele: str
    ) -> Optional[dict[str, Any]]:
        for colocated_variant in annotation.get("colocated_variants", []):
            frequencies = colocated_variant.get("frequencies")
            if frequencies is None or alt_allele not in frequencies:
                continue

            return deepcopy(frequencies[alt_allele])

        return None

    def extract(self) -> Iterator[VEPAnnotationExtractEntry]:
        with open(self._params.file, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue

                annotation = json.loads(line)
                fields = annotation["input"].strip().split("\t")
                chrom = HumanGenome(fields[0])
                pos = int(fields[1])
                ref = fields[3]
                input_alt_alleles = fields[4].split(",")
                annotated_alleles = self.__get_annotated_alleles(
                    annotation, input_alt_alleles
                )

                most_severe_term = annotation.get("most_severe_consequence")
                for alt in annotated_alleles:
                    filtered_annotation = self.__filter_consequences_for_allele(
                        annotation, alt
                    )
                    scores = self.__extract_scores(filtered_annotation)
                    impacted_genes = self.__extract_impacted_genes(
                        filtered_annotation
                    )
                    most_severe_consequence = self.__get_most_severe_consequence(
                        filtered_annotation, most_severe_term
                    )
                    allele_frequency = self.__extract_allele_frequency(annotation, alt)

                    yield VEPAnnotationExtractEntry(
                        chrom=chrom,
                        pos=pos,
                        ref=ref,
                        alt=alt,
                        impacted_genes=impacted_genes,
                        most_severe_consequence=most_severe_consequence,
                        allele_frequency=allele_frequency,
                        annotation=filtered_annotation or None,
                        scores=scores,
                    )

    async def transform(self, data):
        raise NotImplementedError(
            "VEPAnnotationLoader transform stage is not implemented yet; current scope is extract only."
        )

    async def load(self, session, transformed):
        raise NotImplementedError(
            "VEPAnnotationLoader load stage is not implemented yet; current scope is extract only."
        )

    def get_record_id(self, record: VEPAnnotationExtractEntry) -> str:
        return f"{record.chrom.value}:{record.pos}:{record.ref}:{record.alt}"
