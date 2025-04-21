from typing import Optional

from niagads.open_access_api_models.responses.properties import (
    PaginationDataModel,
    RequestDataModel,
)
from niagads.utils.string import is_camel_case
from pydantic import BaseModel, Field


class ViewResponse(BaseModel):
    request: RequestDataModel = Field(
        description="details about the originating request that generated the response"
    )
    pagination: Optional[PaginationDataModel] = Field(
        description="pagination details, if the result is paged"
    )


# FIXME: front end config? extract
def id2title(columnId: str):

    if columnId == "url":
        return "File Download"

    if columnId == "p_value":
        return "p-Value"

    if columnId == "chrom":  # bed file
        return "chrom"
    if is_camel_case(columnId):  # bed file
        return columnId

    if columnId == "biosample_term":
        return "Biosample"

    title = columnId.title().replace("_", " ")
    title = title.replace("Id", "ID").replace("Of", "of").replace("Md5Sum", "md5sum")
    title = title.replace("Url", "URL").replace("Bp ", "BP ")
    if title.startswith("Is "):
        title = title + "?"

    return title
