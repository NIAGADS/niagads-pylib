from pydantic import BaseModel
from typing import Any, List, Optional


class StageTaskSelector(BaseModel):
    stage: str
    task: Optional[str] = None

    @classmethod
    def from_str(cls, value: str):
        if "." in value:
            stage, task = value.split(".", 1)
            return cls(stage=stage, task=task)
        return cls(stage=value)

    @classmethod
    def from_any(cls, value: Any):
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls.from_str(value)
        if isinstance(value, dict):
            return cls(**value)
        raise ValueError(f"Cannot convert {value!r} to StageTaskSelector")

    @classmethod
    def normalize_list(
        cls, items: Optional[List[Any]]
    ) -> Optional[List["StageTaskSelector"]]:
        if items is None:
            return None
        return [cls.from_any(i) for i in items]

    @staticmethod
    def match_stage_task(filters, stage_name, task_name=None):
        if not filters:
            return False
        for f in filters:
            if f.stage == stage_name:
                if f.task is None or f.task == task_name:
                    return True
        return False
