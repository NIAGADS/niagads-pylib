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
from niagads.vep_json_parser.core import VariantVEPAnnotationEntry, VEPJSONParser
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

    def __generate_chunk_text(self, entry: VariantVEPAnnotationEntry):
        # return AnnotationRecord with embedded text (chunk_text) and chunk hash
        ...

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
