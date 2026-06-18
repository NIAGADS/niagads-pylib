import json
from typing import Optional
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.variant.documents import Variant
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, EmbeddingParameterMixin, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from pydantic import Field, field_validator
from niagads.etl.plugins.types import ETLLoadStrategy

from niagads.nlp.llm_types import LLM, NLPModelType


# need to filter consequences for variant allele != variant alt allele
# ditto for allele frequencies
# only is len(colocated_variant >  1)
# af in colocated-variants


class VEPAnnotationLoaderParams(BasePluginParams, PathValidatorMixin, EmbeddingParameterMixin):
    file: str = Field(description="Path to VEP JSON file")
    summarization_model: Optional[LLM] = Field(
        default=LLM.BART_LARGE_CNN, description="LLM model for generating textual summaries of the VEP annotation")
    validate_file_exists = PathValidatorMixin.validator("file")

    @field_validator("prompt_model")
    @classmethod
    def validate_embedding_model(cls, v: LLM) -> LLM:
        """Validate that embedding_model is in allowed embedding models list."""
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

    def extract(self):
        return super().extract()

    async def transform(self, data):
        return await super().transform(data)

    async def load(self, session, transformed):
        return await super().load(session, transformed)
