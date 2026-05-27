from typing import Optional, Union

from niagads.etl.plugins.types import ResumeCheckpoint
from niagads.etl.types import ETLExecutionMode
from niagads.nlp.llm_types import LLM, NLPModelType
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class BasePluginParams(BaseModel):
    """
    Base parameter model for all ETL plugins.

    Attributes:
        batch_size (int): Number of records to buffer before each load/commit in streaming mode.
        log_file (str): Path to the JSON log file for this plugin invocation.
        resume_at (Optional[ResumeFrom]): Resume checkpoint hints, interpreted by plugins (extract/transform).
        run_id (Optional[str]): Pipeline run identifier, provided by the pipeline.
        connection_string (Optional[str]): Database connection string, if needed.

    Note:
        Commit behavior is controlled by the pipeline/CLI via --commit. Plugins should not auto-commit unless instructed.
    """

    mode: Optional[ETLExecutionMode] = Field(
        default=ETLExecutionMode.RUN,
        description=f"The ETL mode; one of {ETLExecutionMode.list()}",
    )
    commit: Optional[bool] = Field(default=False, description="run in commit mode ")
    batch_size: Optional[int] = Field(
        default=5000,
        ge=1,
        description="load batch size; indicates number of records to buffer or bulk insert per commit",
    )
    resume_after: Optional[Union[str, int]] = Field(
        default=None, description="resume checkpoint, a line number or record ID."
    )
    database_uri: Optional[str] = Field(
        default=None,
        description="database connection string; if not provided, the plugin will try to assign from `DATABASE_URI` property in an `.env` file",
    )
    run_id: Optional[int] = Field(
        default=None, description="ETL run ID  (required for UNDO)", exclude=True
    )

    # this shouldn't happen BTW b/c ge validator already set
    @model_validator(mode="after")
    def set_batch_size_none_if_zero(self):
        if self.batch_size == 0:
            self.batch_size = None
        return self

    @staticmethod
    def log_validation_errors(validation_error: ValidationError, logger) -> str:
        errors = [f"--{e['loc'][0]} - {e["msg"]}" for e in validation_error.errors()]
        logger.warning("Invalid parameter values found:")
        for e in validation_error.errors():
            logger.warning(f"--{e['loc'][0]}: {e["msg"]}")
        logger.exception("Failed to initializing plugin.")


class PathValidatorMixin:
    """
    Mixin for Pydantic models to provide a reusable file or directory existence validator.

    Usage:
        - Inherit from this mixin in your parameter model.
        - Attach the validator to any field by specifying the field name (e.g., 'file'):

            validate_file_exists = PathValidatorMixin.validator('file')

        - You can use a different field name for other models:

            validate_input_path_exists = PathValidatorMixin.validator('input_path', is_dir=True)

    Args:
        field_name (str): The name of the field to validate.
        is_dir (bool, optional):
            - If False (default), validates that the field value is an existing file.
            - If True, validates that the field value is an existing directory or path.

    The validator will raise a ValueError if the file or directory does not exist.
    """

    @classmethod
    def validator(cls, field_name):
        @field_validator(field_name, mode="plain")
        def file_exists(cls, value):
            from niagads.utils.sys import verify_path

            if not verify_path(value):
                raise ValueError(f"Unable to access {value}; path does not exist.")
            return value

        return file_exists


class EmbeddingParameterMixin:
    """
    Mixin for ETL plugin parameter models to add embedding model configuration.

    Provides fields and validation for specifying the LLM embedding model and batch size
    for text embedding generation in ETL workflows.

    Attributes:
        embedding_model (Optional[LLM]): LLM model for generating text embeddings.
        embedding_batch_size (Optional[int]): Batch size for calculating embeddings.

    Methods:
        validate_embedding_model: Validates that the embedding model is allowed for embedding tasks.
    """

    embedding_model: Optional[LLM] = Field(
        LLM.ALL_MINILM_L6_V2,
        description="LLM model for generating text embeddings",
    )
    embedding_batch_size: Optional[int] = Field(
        default=128, description="batch size for calculating embeddings"
    )

    @field_validator("embedding_model")
    @classmethod
    def validate_embedding_model(cls, v: LLM) -> LLM:
        """Validate that embedding_model is in allowed embedding models list."""
        LLM.validate(v, NLPModelType.EMBEDDING)
        return LLM(v)
