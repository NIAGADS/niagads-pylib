from .selectors import StageTaskSelector
from typing import Any, List, Optional, Dict


class PipelineFilters:
    def __init__(self, only=None, skip=None, resume_point=None):
        self._only = StageTaskSelector.normalize_list(only)
        self._skip = StageTaskSelector.normalize_list(skip)
        self._resume_point = StageTaskSelector.from_any(resume_point)

    @property
    def only(self):
        return self._only

    @only.setter
    def only(self, value):
        self._only = StageTaskSelector.normalize_list(value)

    @property
    def skip(self):
        return self._skip

    @skip.setter
    def skip(self, value):
        self._skip = StageTaskSelector.normalize_list(value)

    @property
    def resume_point(self):
        return self._resume_point

    @resume_point.setter
    def resume_point(self, value):
        self._resume_point = StageTaskSelector.from_any(value)

    def validate(self, config_stages):
        """
        Validates the filter configuration against the pipeline stages.

        Args:
            config_stages (list): List of StageConfig objects representing pipeline stages.

        Raises:
            ValueError: If both 'only' and 'skip' filters are set, or if resume_point refers to a skipped/deprecated stage/task, or if resume_point is not found.
        """
        if self._only and self._skip:
            raise ValueError(
                "Cannot set both 'only' and 'skip' filters; they are mutually exclusive."
            )

        if self._resume_point:
            selector = self._resume_point
            for stage in config_stages:
                if stage.name == selector.stage:
                    if stage.skip or stage.deprecated:
                        raise ValueError(
                            f"Cannot resume at skipped or deprecated stage: {selector.stage}"
                        )
                    if selector.task:
                        found = False
                        for task in stage.tasks:
                            if task.name == selector.task:
                                found = True
                                if task.skip or task.deprecated:
                                    raise ValueError(
                                        f"Cannot resume at skipped or deprecated task: {selector.stage}.{selector.task}"
                                    )
                        if not found:
                            raise ValueError(
                                f"Task not found for resume_point: {selector.stage}.{selector.task}"
                            )
                    break
            else:
                raise ValueError(f"Stage not found for resume_point: {selector.stage}")
