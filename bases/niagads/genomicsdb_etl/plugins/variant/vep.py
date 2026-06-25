import json
from copy import deepcopy
from typing import Any, Iterator, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    EmbeddingParameterMixin,
    PathValidatorMixin,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genome_reference.human import HumanGenome
from niagads.nlp.llm_types import LLM, NLPModelType
from niagads.utils.sys import read_open_ctx
from niagads.vcf.types import VCFEntry
from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    "loftool",
]


class ImpactedGene(BaseModel):
    gene_id: str
    gene_symbol: Optional[str] = None
    loftool: Optional[float] = None

    model_config = ConfigDict(extra="forbid")


class ConsequenceArrays(BaseModel):
    transcript_consequences: Optional[list[dict]] = None
    intergenic_consequences: Optional[list[dict]] = None
    regulatory_feature_consequences: Optional[list[dict]] = None
    motif_feature_consequences: Optional[list[dict]] = None


class Annotation(BaseModel, ConsequenceArrays):
    scores: Optional[dict] = None


class AnnotationEntry(BaseModel):
    positional_id: str
    chrom: HumanGenome
    pos: int
    ref: str
    alt: str
    impacted_genes: Optional[list[ImpactedGene]] = None
    most_severe_consequence: Optional[dict[str, Any]] = None
    allele_frequency: Optional[dict[str, Any]] = None
    annotation: Optional[Annotation] = None

    model_config = ConfigDict(extra="forbid")


class VEPEntry(ConsequenceArrays):
    id: str
    seq_region_name: str
    start: int
    end: int
    strand: int
    allele_string: str
    assembly_name: str
    variant_class: str
    most_severe_consequence: str
    input: VCFEntry
    colocated_variants: Optional[list[dict]] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("input", mode="before")
    @classmethod
    def parse_input_to_vcf_entry(cls, v: Any) -> VCFEntry:
        """transform VCF input string into VCFEntry object."""
        if isinstance(v, VCFEntry):
            return v
        if isinstance(v, str):
            return VCFEntry.from_line(v)


class VEPAnnotationLoaderParams(
    BasePluginParams, PathValidatorMixin, EmbeddingParameterMixin
):
    file: str = Field(description="Path to VEP JSON file")
    summarization_model: Optional[LLM] = Field(
        default=LLM.BART_LARGE_CNN,
        description="LLM model for generating textual summaries of the VEP annotation",
    )
    validate_file_exists = PathValidatorMixin.validator("file")

    @field_validator("summarization_model")
    @classmethod
    def validate_embedding_model(cls, v: LLM) -> LLM:
        """Validate that summarization_model is in allowed summarization models list."""
        LLM.validate(v, NLPModelType.SUMMARIZATION)
        return LLM(v)


metadata = PluginMetadata(
    version="1.0",
    description=f"Update existing {Variant.table_name()} records with VEP annotation."
    "Includes translating to human readable text and calculating embeddings",
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

    def extract(self) -> Iterator[AnnotationEntry]:
        with read_open_ctx(self._params.file) as fh:
            for line in enumerate(fh):
                annotation = VEPEntry(**json.loads(line.rstrip()))

                chromosome = annotation.input.chrom
                position = annotation.input.pos
                ref = annotation.input.ref
                alt_alleles: list[str] = annotation.input.alt

                for alt in alt_alleles:
                    entry = AnnotationEntry(
                        positional_id=f"{chromosome}:{position}:{ref}:{alt}",
                        chromosome=chromosome,
                        position=position,
                        ref=ref,
                        alt=alt,
                    )

                    # extract variant specific annotations

    async def transform(self, data): ...

    async def load(self, session, transformed): ...

    def get_record_id(self, record: AnnotationEntry) -> str:
        return record.positional_id
