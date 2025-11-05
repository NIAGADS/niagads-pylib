from typing import Optional
from niagads.etl.config import ETLMode
from pydantic import BaseModel, Field, model_validator, field_validator


class ResumeCheckpoint(BaseModel):
    """
    Resume checkpoint.
    - Use 'line' for source-relative resume (handled in extract()).
    - Use 'record' for domain resume (handled in extract() or load()).
    """

    line: Optional[int] = Field(
        None,
        description="Line number (1-based) to resume from; header not included in count",
    )
    record: Optional[str] = Field(
        None, description="Natural identifier or full record to resume from"
    )
    full_record: Optional[dict]

    @model_validator(mode="after")
    def validate_checkpoint(self):
        if not self.line and not self.record:
            raise ValueError("checkpoint must define either 'line' or 'record'")
        return self


class BasePluginParams(BaseModel):
    """
    Base parameter model for all ETL plugins.

    Attributes:
        commit_after (int): Number of records to buffer before each load/commit in streaming mode.
        log_file (str): Path to the JSON log file for this plugin invocation.
        checkpoint (Optional[ResumeFrom]): Resume checkpoint hints, interpreted by plugins (extract/transform).
        run_id (Optional[str]): Pipeline run identifier, provided by the pipeline.
        connection_string (Optional[str]): Database connection string, if needed.

    Note:
        Commit behavior is controlled by the pipeline/CLI via --commit. Plugins should not auto-commit unless instructed.
    """

    mode: ETLMode = Field(
        default=ETLMode.DRY_RUN, description=f"The ETL mode; one of {ETLMode.list()}"
    )
    commit_after: Optional[int] = Field(
        default=10000, ge=1, description="records to buffer per commit"
    )
    log_path: Optional[str] = Field(
        default=None,
        description="Path to log file for the plugin.  If does not end in `.log`, assumes `log-path` is a directory and will write to `{log-path}/{plugin-name}.log",
    )
    resume_checkpoint: Optional[ResumeCheckpoint] = Field(
        default=None,
        description="resume checkpoint, a line number or record ID.  Indicate as line=<N> or id=<record ID>",
    )
    run_id: Optional[str] = Field(
        default=None,
        description="optional run identifier, provided by pipeline manager when run in pipeline",
    )
    connection_string: Optional[str] = Field(
        default=None,
        description="database connection string; if not provided, the plugin will try to assign from `DATABASE_URI` property in an `.env` file",
    )
    verbose: Optional[bool] = Field(default=False, description="run in verbose mode")
    debug: Optional[bool] = Field(default=False, description="run in debug mode")

    # this shouldn't happen BTW b/c ge validator already set
    @model_validator(mode="after")
    def set_commit_after_none_if_zero(self):
        if self.commit_after == 0:
            self.commit_after = None
        return self


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
    def validator(cls, field_name, is_dir=False):
        @field_validator(field_name)
        def file_exists(cls, value):
            from niagads.utils.sys import verify_path

            if not verify_path(value, isDir=is_dir):
                target_type = "Directory" if is_dir else "File"
                raise ValueError(f"{target_type} does not exist: {value}")
            return value

        return file_exists
