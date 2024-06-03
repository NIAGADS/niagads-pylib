from pydantic import BaseModel
from typing import Optional

# TODO: common params: https://fastapi.tiangolo.com/tutorial/dependencies/classes-as-dependencies/
class OptionalParams(BaseModel):
    limit: Optional[int] = None
    page: Optional[int] = None
    countOnly: Optional[bool] = False
    