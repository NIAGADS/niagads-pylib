from enum import auto
from typing import Optional, Dict, Any, List, Literal, Type
from pydantic import BaseModel, Field, field_validator
from niagads.enums.core import CaseInsensitiveEnum


class TaskType(CaseInsensitiveEnum):
    """
    Task type for pipeline tasks:
    - PLUGIN:     Run a registered plugin (default)
    - SHELL:      Run a shell command
    - FILE:       Perform a file operation (exists, copy, move, etc.)
    - VALIDATION: Run a custom validation callable
    - NOTIFY:     Send a notification (e.g., Slack, email, webhook)
    """

    PLUGIN = auto()
    SHELL = auto()
    FILE = auto()
    VALIDATION = auto()
    NOTIFY = auto()


class ParallelMode(CaseInsensitiveEnum):
    """
    Task execution strategy:
    - NONE:    sequential execution
    - THREAD:  thread pool concurrency (I/O-bound workloads)
    - PROCESS: process pool concurrency (CPU-bound workloads)
    """

    NONE = auto()
    THREAD = auto()
    PROCESS = auto()


class TaskConfig(BaseModel):
    """
    Task config. Default type is 'plugin'. Other types do not use DB.
    """

    name: str = Field(..., description="Task name (unique within stage)")
    type: TaskType = TaskType.PLUGIN
    plugin: Optional[str] = Field(
        None, description="Plugin class name (required if type='plugin')"
    )
    params: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Task parameters (plugin/file/validator/notify)",
    )
    skip: Optional[bool] = Field(False, description="Skip this task")
    deprecated: Optional[bool] = Field(False, description="Mark task deprecated")
    comment: Optional[str] = Field(None, description="Task annotation/comment")

    # Non-plugin fields (shell/file/validation/notify)
    command: Optional[str] = Field(None, description="Shell command (type='shell')")
    path: Optional[str] = Field(None, description="File path (type='file')")
    action: Optional[str] = Field(None, description="Validation or file action")
    channel: Optional[str] = Field(None, description="Notification channel/endpoint")
    message: Optional[str] = Field(None, description="Notification message/payload")

    @field_validator("plugin")
    @classmethod
    def require_plugin_if_type_plugin(cls, v, info):
        if info.data.get("type") == "plugin" and not v:
            raise ValueError("Plugin task must define 'plugin'")
        return v


class StageConfig(BaseModel):
    """
    Stage config — barrier semantics:
    - If any task fails in the stage, the stage fails and the pipeline stops.
    """

    name: str = Field(..., description="Stage name")
    parallel_mode: ParallelMode = Field(
        ParallelMode.NONE, description="Execution mode for tasks"
    )
    max_concurrency: Optional[int] = Field(
        None, ge=1, description="Max concurrency when parallel_mode='async'"
    )
    tasks: List[TaskConfig] = Field(..., description="Tasks in this stage")
    skip: bool = Field(False, description="Skip this stage")
    deprecated: bool = Field(False, description="Mark this stage as deprecated")
    comment: Optional[str] = Field(None, description="Stage-level annotation/comment")


class PipelineConfig(BaseModel):
    """
    Pipeline config.
    - params are pipeline-level defaults; tasks can reference via ${...} interpolation.
    """

    params: Dict[str, Any] = Field(
        default_factory=dict, description="Pipeline-level parameters"
    )
    stages: List[StageConfig] = Field(..., description="Pipeline stages")
    comment: Optional[str] = Field(
        None, description="Pipeline-level annotation/comment"
    )
