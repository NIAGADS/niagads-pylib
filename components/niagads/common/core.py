from typing import Optional
from niagads.utils.dict import prune
from pydantic import BaseModel, ConfigDict, model_serializer


class NullFreeModel(BaseModel):
    """a pydantic model where attributes with NULL values (e.g., None, 'NULL') are removed during serialization"""

    model_config = ConfigDict(exclude_none=True)
