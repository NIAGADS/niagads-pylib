import json
from typing import Iterator, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.mixins import EmbeddingGeneratorContextMixin
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    EmbeddingParameterMixin,
    PathValidatorMixin,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.nlp.llm_types import LLM, NLPModelType
from niagads.nlp.models import SummaryPrompt
from niagads.nlp.summarization import TextSummaryGenerator
from niagads.utils.sys import read_open_ctx
from niagads.vep_json_parser.core import (
    Consequence,
    ConsequenceType,
    TranscriptContext,
    VariantVEPAnnotationEntry,
    VEPJSONParser,
)
from pydantic import BaseModel, Field, field_validator


class AnnotationRecord(BaseModel, arbitrary_types_allowed=True):
    annotation: VariantVEPAnnotationEntry
    chunk_text: str
    chunk_hash: bytes
    embedding: Optional[list] = None  # so it can be set in batch
    summart_text: Optional[str] = None


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
class VEPAnnotationLoader(AbstractBasePlugin, EmbeddingGeneratorContextMixin):
    _params: VEPAnnotationLoaderParams

    def __init__(self, params, name=None, log_path=None, debug=False, verbose=False):
        super().__init__(params, name, log_path, debug, verbose)
        self._summary_generator: Optional[TextSummaryGenerator] = None

    async def on_run_start(self, session):
        self._summary_generator = TextSummaryGenerator(
            model=self._params.summarization_model,
            debug=self._debug,
            verbose=self._verbose,
            logger=self.logger,
        )

    def extract(self) -> Iterator[VariantVEPAnnotationEntry]:
        parser = VEPJSONParser()
        with read_open_ctx(self._params.file) as fh:
            line: str
            for line in enumerate(fh):
                allele_annotations: dict[str, VariantVEPAnnotationEntry] = parser.parse(
                    line.rstrip()
                )
                batch = []
                for annotation in allele_annotations.values():
                    batch.append(annotation)
                    if len(batch) == self._params.embedding_batch_size:
                        yield batch
                # yield residuals
                yield batch

    def __tss_distance_phrases(self, tssdistance: int | None) -> list[str]:
        if tssdistance is None:
            return []

        if tssdistance <= 1000:
            return ["Near transcription start site.", "Within 1kb of TSS."]

        if tssdistance <= 10000:
            return ["Near transcription start site.", "Within 10kb of TSS."]

        if tssdistance <= 100000:
            return [
                "Proximal to transcription start site.",
                "Within 100kb of TSS.",
            ]

        return [
            "Distal from transcription start site.",
            "More than 100kb from TSS.",
        ]

    def __gene_distance_phrases(self, distance: int | None) -> list[str]:
        if distance is None:
            return []

        if distance <= 1000:
            return ["Near gene.", "Within 1kb of gene."]

        if distance <= 10000:
            return ["Near gene.", "Within 10kb of gene."]

        if distance <= 100000:
            return ["Proximal to gene.", "Within 100kb of gene."]

        return ["Distal from gene.", "More than 100kb from gene."]

    def __af_descriptor(self, value: float) -> str:
        if value < 0.001:
            return "very rare"

        if value < 0.01:
            return "rare"

        if value < 0.05:
            return "low frequency"

        return "common"

    def __af_phrases(self, allele_frequency: dict | None) -> list[str]:
        if allele_frequency is None:
            return []

        phrases = []

        source: str
        for source, populations in allele_frequency.items():
            population: str
            for population, value in (populations or {}).items():
                if value == 0:
                    continue

                af_qualifier = self.__af_descriptor(value)

                phrases.append(
                    f"{source} {population.upper()} allele frequency {af_qualifier}."
                )

        return phrases

    def __deleteriousness_phrases_from_cadd(
        self, cadd_phred: float | None
    ) -> list[str]:
        if cadd_phred is None:
            return []

        if cadd_phred >= 30:
            return [
                "Very strong predicted deleteriousness.",
                "Top 0.1 percent of possible reference variants.",
            ]

        if cadd_phred >= 20:
            return [
                "Strong predicted deleteriousness.",
                "Top 1 percent of possible reference variants.",
            ]

        if cadd_phred >= 10:
            return [
                "Moderate predicted deleteriousness.",
                "Top 10 percent of possible reference variants.",
            ]

        return [
            "Weak predicted deleteriousness.",
            "Below top 10 percent of possible reference variants.",
        ]

    def __regulatory_effect_phrases_from_enformer(
        self, sad: float | None, sar: float | None
    ) -> list[str]:
        values = [abs(value) for value in (sad, sar) if value is not None]
        if not values:
            return []

        max_abs = max(values)

        if max_abs < 0.01:
            return ["Minimal predicted regulatory effect."]

        if max_abs < 0.1:
            return ["Small predicted regulatory effect."]

        return ["Strong predicted regulatory effect."]

    def __loftool_phrases(self, loftool: float | int | None) -> list[str]:
        if loftool is None:
            return []

        if loftool < 0.1:
            return ["Gene shows high loss-of-function intolerance."]

        if loftool < 0.5:
            return ["Gene shows moderate loss-of-function intolerance."]

        return ["Gene shows low loss-of-function intolerance."]

    def __unique_regulatory_biotypes(
        self, entry: VariantVEPAnnotationEntry
    ) -> list[str]:

        regulatory_consequences = (
            entry.predicted_annotations.predicted_consequences.get(
                ConsequenceType.REGULATORY_FEATURE
            )
        )
        if regulatory_consequences is None:
            return []

        biotypes = {
            consequence.feature.biotype
            for consequence in regulatory_consequences
            if consequence.feature is not None
        }

        return sorted(biotypes)

    def __coding_change_phrases(feature: TranscriptContext) -> list[str] | None:
        phrases = []

        if feature.codons:
            phrases.append(f"Codon change {feature.codons}")

        protein = feature.protein

        if protein and protein.amino_acids:
            phrases.append(f"Amino acid change {protein.amino_acids}")

        return phrases

    def __transcript_msc_phrases(self, consequence: Consequence) -> list[str]:
        phrases = []
        transcript = consequence.feature
        gene = transcript.gene
        protein = transcript.protein

        phrases.append(f"Transcript ID {transcript.id}.")
        phrases.append(
            f"Transcript consequence {', '.join(consequence.consequence_terms)}."
        )
        phrases.append(f"Impact {consequence.impact}.")

        if consequence.is_coding is True:
            phrases.append("Coding consequence.")
            phrases.append(self.__coding_change_phrases(transcript))

        elif consequence.is_coding is False:
            phrases.append("Noncoding consequence.")

        if gene is not None:  # should never be false
            phrases.append(f"Gene ID {gene.id}.")
            phrases.append(f"Gene biotype {gene.biotype}.")
            if gene.gene_symbol:
                phrases.append(f"Gene {gene.gene_symbol}.")

            phrases.extend(self.__loftool_phrases(gene.loftool))

        if protein is not None:
            phrases.append("Protein consequence.")

            if protein.id:
                phrases.append(f"Protein {protein.id}.")

        phrases.extend(self.__tss_distance_phrases(transcript.tssdistance))
        phrases.extend(self.__gene_distance_phrases(transcript.distance))

        return phrases

    def __regulatory_biotype_phrases(self, biotypes: list[str]) -> list[str]:
        if not biotypes:
            return []

        return ["Regulatory feature biotypes " + ", ".join(biotypes) + "."]

    def __intergenic_msc_phrases(self, consequence: Consequence) -> list[str]:
        phrases = []

        if consequence.consequence_terms:
            phrases.append(
                f"Intergenic consequence {', '.join(consequence.consequence_terms)}."
            )

        if consequence.impact:
            phrases.append(f"Impact {consequence.impact}.")

        return phrases

    def __consequence_phrases(self, consequence: Consequence) -> list[str]:
        phrases = []

        if consequence.consequence_terms:
            phrases.append(f"Consequence {', '.join(consequence.consequence_terms)}.")

        if consequence.impact:
            phrases.append(f"Impact {consequence.impact}.")

        return phrases

    def __predictor_score_phrases(self, entry: VariantVEPAnnotationEntry) -> list[str]:
        scores = entry.predicted_annotations.predictor_scores
        if scores is None:
            return []

        phrases = self.__deleteriousness_phrases_from_cadd(scores.get("cadd_phred"))
        phrases.extend(
            self.__regulatory_effect_phrases_from_enformer(
                scores.get("enformer_sad"),
                scores.get("enformer_sar"),
            )
        )
        return phrases

    def __most_severe_consequence_phrases(
        self, entry: VariantVEPAnnotationEntry
    ) -> list[str]:
        msc: Consequence = entry.most_severe_consequence

        consequence_type = msc.consequence_type

        if consequence_type == ConsequenceType.INTERGENIC:
            return self.__intergenic_msc_phrases(msc)

        if consequence_type == ConsequenceType.TRANSCRIPT:
            msc_phrases = self.__transcript_msc_phrases(msc)
            msc_phrases.extend(
                self.__regulatory_biotype_phrases(
                    self.__unique_regulatory_biotypes(entry)
                )
            )
            return msc_phrases

        if consequence_type == ConsequenceType.REGULATORY_FEATURE:
            return self.__regulatory_biotype_phrases(
                self.__unique_regulatory_biotypes(entry)
            )

        return self.__consequence_phrases(msc)

    def __generate_chunk_text(self, entry: VariantVEPAnnotationEntry):
        # return AnnotationRecord with embedded text (chunk_text) and chunk hash
        annotation_phrases = []
        annotation_phrases.extend(self.__most_severe_consequence_phrases(entry))
        annotation_phrases.extend(self.__af_phrases(entry.allele_frequency))
        annotation_phrases.extend(self.__predictor_score_phrases(entry))

        chunk_text = "\n".join(annotation_phrases)

        if self._verbose:
            self.logger.debug(f"Chunk Text: {chunk_text}")

        # TODO - possibly add human readable summary

        return AnnotationRecord(
            annotation=entry,
            chunk_text=chunk_text,
            chunk_hash=self._embedding_generator.hash_text(chunk_text),
        )

    async def transform(self, entries: list[VariantVEPAnnotationEntry]):
        records: list[AnnotationRecord] = []
        text = []
        for entry in entries:
            annotation_record: AnnotationRecord = self.__generate_chunk_text(entry)

            records.append(annotation_record)
            text.append(annotation_record.chunk_text)

        embeddings = self._embedding_generator.generate(text, as_list=False)

        record: AnnotationRecord
        for index, record in enumerate(records):
            record.embedding = embeddings[index].tolist()

        self.__processed_record_count += self._params.embedding_batch_size
        self.logger.info(
            f"Calcualted embeddings for {self.__processed_record_count} annotations."
        )

        return records

    async def load(self, session, transformed): ...

    def get_record_id(self, record: VariantVEPAnnotationEntry) -> str:
        return record.positional_id
