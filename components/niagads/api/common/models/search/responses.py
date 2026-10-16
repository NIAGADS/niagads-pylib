from typing import Generic, List

from niagads.api.common.models.records.types import RecordT
from niagads.common.models.base import CustomBaseModel

from components.niagads.common.search.models.record import SearchMatch
from niagads.api.common.models.responses.data import DataResponse


class SearchMatchResponse(DataResponse):
    data: List[SearchMatch]

    def to_delimited_text(self, *, incl_header=False, null_str="NA"):
        raise NotImplementedError(
            "TEXT formatted output not available for a search result response."
        )


class RecordLookupResponse(CustomBaseModel, Generic[RecordT]):
    """
    Generic Response for bulk record retrieval
    example usage:
    @router.post(
    "/genes/lookup",
    response_model=RecordLookupResponse[Gene],
    )
    async def lookup_genes(...) -> RecordLookupResponse[Gene]:
    ...

    """

    lookup: list[list[RecordT] | None]
