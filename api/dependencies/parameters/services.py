from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


from api.response_models.base_models import RequestDataModel
from api.common.formatters import clean
class InternalRequestParameters(BaseModel, arbitrary_types_allowed=True):
    requestData: RequestDataModel = Depends(RequestDataModel.from_request)
    session: AsyncSession