from typing import List, Optional, Type
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.etl.plugins.types import ETLLoadStrategy, ETLOperation
from pydantic import BaseModel
from sqlalchemy.orm import DeclarativeBase


class PluginMetadata(BaseModel, arbitrary_types_allowed=True):

    version: str
    description: str
    affected_tables: Optional[List[Type[DeclarativeBase]]] = None
    load_strategy: ETLLoadStrategy
    operation: ETLOperation
    is_large_dataset: bool = False
    parameter_model: Type[BasePluginParams]
