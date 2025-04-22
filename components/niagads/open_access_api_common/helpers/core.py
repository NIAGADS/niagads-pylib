from fastapi.exceptions import RequestValidationError
from fastapi import Response, status
from pydantic import BaseModel, field_validator, ConfigDict, model_validator
from typing import Any, Dict, Optional, Type, Union

from niagads.utils.list import list_to_string
from sqlalchemy import RowMapping

from api.common.constants import DEFAULT_PAGE_SIZE, MAX_NUM_PAGES
from api.common.enums.cache import CacheKeyQualifier, CacheNamespace
from api.common.enums.database import DataStore
from api.common.enums.response_properties import (
    ResponseContent,
    ResponseView,
    ResponseFormat,
)
from api.common.services.metadata_query import MetadataQueryService
from api.common.types import Range

from api.dependencies.parameters.services import InternalRequestParameters
from api.models.base_row_models import DynamicRowModel
from api.models.response_model_properties import CacheKeyDataModel, PaginationDataModel
from api.models.base_response_models import ResponseModel, T_ResponseModel
from api.models.igvbrowser import IGVBrowserTrackSelectorResponse
from api.models.view_models import TableViewResponse

INTERNAL_PARAMETERS = ["span", "_tracks"]


class PaginationCursor(BaseModel):
    """pagination cursor"""

    key: Union[str, int]
    offset: Optional[int] = None


class Parameters(BaseModel):
    """arbitrary namespace to store request parameters and pass them to helpers"""

    __pydantic_extra__: Dict[str, Any]
    model_config = ConfigDict(extra="allow")

    def get(self, attribute: str, default: Any = None):
        if attribute in self.model_extra:
            return self.model_extra[attribute]
        else:
            return default

    def update(self, attribute: str, value: Any):
        self.model_extra[attribute] = value


class RouteHelper:

    def __init__(
        self,
        managers: InternalRequestParameters,
        responseConfig: ResponseConfiguration,
        params: Parameters,
    ):
        self._managers: InternalRequestParameters = managers
        self._responseConfig: ResponseConfiguration = responseConfig
        self._pagination: PaginationDataModel = None
        self._parameters: Parameters = params
        self._pageSize: int = DEFAULT_PAGE_SIZE
        self._resultSize: int = None

    def _sqa_row2dict(self, result):
        # row = lambda r: {c.name: str(getattr(r, c.name)) for c in r.__table__.columns}
        if "ResponseModel" in str(self._responseConfig.model):
            if isinstance(result[0], RowMapping):
                return [DynamicRowModel(**row) for row in result]

        return result

    def set_page_size(self, pageSize: int):
        self._pageSize = pageSize

    async def _get_cached_response(self):
        cacheKey = self._managers.cacheKey.encrypt()
        response = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if response is not None:
            return await self.generate_response(response, isCached=True)

        return None

    def _pagination_exists(self, raiseError: bool = True):
        if self._pagination is None:
            if raiseError:
                raise RuntimeError(
                    "Attempting to modify or access pagination before initializing"
                )
            else:
                return False
        return True

    def _is_valid_page(self, page: int):
        """test if the page is valid (w/in range of expected number of pages)"""

        self._pagination_exists()

        if self._pagination.total_num_pages is None:
            raise RuntimeError(
                "Attempting fetch a page before estimating total number of pages"
            )

        if page > self._pagination.total_num_pages:
            raise RequestValidationError(
                f"Request `page` {page} does not exist; this query generates a maximum of {self._pagination.total_num_pages} pages"
            )

        return True

    def page(self):
        if self._parameters is not None:
            return self._parameters.get("page", 1)
        return 1

    def total_num_pages(self):
        if self._resultSize is None:
            raise RuntimeError("Attempting to page before estimating result size.")

        if self._resultSize > self._pageSize * MAX_NUM_PAGES:
            raise RequestValidationError(
                f"Result size ({self._resultSize}) is too large; filter for fewer tracks or narrow the queried genomic region."
            )

        return (
            1
            if self._resultSize < self._pageSize
            else next(
                (
                    p
                    for p in range(1, MAX_NUM_PAGES)
                    if (p - 1) * self._pageSize > self._resultSize
                )
            )
            - 1
        )

    def initialize_pagination(self, raiseError=True):
        """returns False if not a paged model and raiseError = False"""
        if self._responseConfig.model.is_paged():
            self._pagination = PaginationDataModel(
                page=self.page(),
                total_num_pages=self.total_num_pages(),
                paged_num_records=None,
                total_num_records=self._resultSize,
            )

            return self._is_valid_page(self._pagination.page)
        else:
            if raiseError:
                raise RuntimeError("Attempt to page a non-pageable response model")
            return False

    def set_paged_num_records(self, numRecords: int):
        self._pagination_exists()
        self._pagination.paged_num_records = numRecords

    def offset(self):
        """calculate offset for SQL pagination"""
        self._pagination_exists()
        return (
            None
            if self._pagination.page == 1
            else (self._pagination.page - 1) * self._pageSize
        )

    def slice_result_by_page(self, page: int = None) -> Range:
        """calculates start and end indexes for paging an array"""
        self._pagination_exists()
        targetPage = self._pagination.page if page is None else page
        start = (targetPage - 1) * self._pageSize
        end = (
            start + self._pageSize
        )  # don't subtract 1 b/c python slices are not end-range inclusive
        if end > self._resultSize:
            end = self._resultSize

        return Range(start=start, end=end)

    async def generate_table_response(self, response: Type[T_ResponseModel]):
        # create an encrypted cache key
        cacheKey = CacheKeyDataModel.encrypt_key(
            self._managers.cacheKey.key
            + str(CacheKeyQualifier.VIEW)
            + ResponseView.TABLE.value
        )

        viewResponse = await self._managers.cache.get(
            cacheKey, namespace=CacheNamespace.VIEW
        )

        if viewResponse:
            return viewResponse

        self._managers.requestData.set_request_id(cacheKey)

        if self._responseConfig.format != ResponseFormat.JSON:
            self._managers.requestData.add_message(
                f"WARNING: `Table` VIEW requested; response format changed to `{ResponseFormat.JSON.value}`"
            )

        viewResponseObj = {
            "response": response.to_view(ResponseView.TABLE, id=cacheKey),
            "request": self._managers.requestData,
            "pagination": response.pagination if response.is_paged() else None,
        }

        viewResponse = TableViewResponse(**viewResponseObj)

        await self._managers.cache.set(
            cacheKey, viewResponse, namespace=CacheNamespace.VIEW
        )

        return viewResponse

    async def generate_response(self, result: Any, isCached=False):
        response: Type[T_ResponseModel] = result if isCached else None
        if response is None:
            self._managers.requestData.update_parameters(
                self._parameters, exclude=INTERNAL_PARAMETERS
            )

            if self._responseConfig.model.is_paged():
                if not self._pagination_exists(raiseError=False):
                    if self._resultSize is None:
                        self._resultSize = len(result)

                    self.initialize_pagination()

                self.set_paged_num_records(len(result))

                response = self._responseConfig.model(
                    request=self._managers.requestData,
                    pagination=self._pagination,
                    data=self._sqa_row2dict(result),
                )
            else:
                if self._responseConfig.model == IGVBrowserTrackSelectorResponse:
                    queryId = self._managers.cacheKey.encrypt()
                    collectionId = self._parameters.get("collection")

                    response = self._responseConfig.model(
                        request=self._managers.requestData,
                        data=IGVBrowserTrackSelectorResponse.build_table(
                            result, queryId if collectionId is None else collectionId
                        ),
                    )
                else:
                    response = self._responseConfig.model(
                        request=self._managers.requestData,
                        data=self._sqa_row2dict(result),
                    )

            # cache the response
            await self._managers.cache.set(
                self._managers.cacheKey.encrypt(),
                response,
                namespace=self._managers.cacheKey.namespace,
            )

        match self._responseConfig.view:
            case ResponseView.TABLE:
                return await self.generate_table_response(response)

            case ResponseView.DEFAULT:
                if self._responseConfig.format in [
                    ResponseFormat.TEXT,
                    ResponseFormat.BED,
                    ResponseFormat.VCF,
                ]:
                    try:
                        nullStr = (
                            None
                            if self._responseConfig.format == ResponseFormat.TEXT
                            else "."
                        )
                        return Response(
                            response.to_text(
                                self._responseConfig.format, nullStr=nullStr
                            ),
                            media_type="text/plain",
                        )
                    except NotImplementedError as err:
                        if self._responseConfig.format == ResponseFormat.TEXT:
                            response.add_message(
                                f"{str(err)} Returning default JSON response."
                            )
                            return response
                        else:
                            raise err
                else:  # JSON
                    return response

            case _:  # IGV_BROWSER
                raise NotImplementedError(
                    f"A response for view of type {str(self._responseConfig.view)} is coming soon."
                )


class MetadataRouteHelper(RouteHelper):
    """RouteHelper extended w/Metadata queries"""

    def __init__(
        self,
        managers: InternalRequestParameters,
        responseConfig: ResponseConfiguration,
        params: Parameters,
        dataStore=[DataStore.SHARED],
    ):
        super().__init__(managers, responseConfig, params)
        self._dataStore = dataStore

    async def get_track_metadata(self, rawResponse=False):
        """fetch track metadata; expects a list of track identifiers in the parameters"""
        isCached = True  # assuming true from the start
        cacheKey = self._managers.cacheKey.encrypt()
        if rawResponse:
            cacheKey += CacheKeyQualifier.RAW

        result = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if result is None:
            isCached = False

            tracks = self._parameters.get("_tracks", self._parameters.get("track"))
            tracks = tracks.split(",") if isinstance(tracks, str) else tracks
            tracks = sorted(tracks)  # best for caching & pagination

            result = await MetadataQueryService(
                self._managers.metadataSession, dataStore=self._dataStore
            ).get_track_metadata(tracks, responseType=self._responseConfig.content)

            if not rawResponse:
                self._resultSize = len(result)
                pageResponse = self.initialize_pagination(raiseError=False)
                if pageResponse:
                    sliceRange = self.slice_result_by_page()
                    result = result[sliceRange.start : sliceRange.end]

        if rawResponse:
            # cache the raw response
            await self._managers.cache.set(
                cacheKey, result, namespace=self._managers.cacheKey.namespace
            )

            return result

        return await self.generate_response(result, isCached=isCached)

    # FIXME: not sure if this will ever need a "rawResponse"
    async def get_collection_track_metadata(self, rawResponse=False):
        """fetch track metadata for a specific collection"""
        isCached = True  # assuming true from the start
        cacheKey = self._managers.cacheKey.encrypt()
        if rawResponse:
            cacheKey += CacheKeyQualifier.RAW + "_" + str(rawResponse)

        result = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if result is None:
            isCached = False

            result = await MetadataQueryService(
                self._managers.metadataSession,
                self._managers.requestData,
                self._dataStore,
            ).get_collection_track_metadata(
                self._parameters.collection,
                self._parameters.track,
                responseType=self._responseConfig.content,
            )

            if not rawResponse:
                self._resultSize = len(result)
                pageResponse = self.initialize_pagination(raiseError=False)
                if pageResponse:
                    sliceRange = self.slice_result_by_page()
                    result = result[sliceRange.start : sliceRange.end]

        if rawResponse:
            # cache the raw response
            await self._managers.cache.set(
                cacheKey, result, namespace=self._managers.cacheKey.namespace
            )
            return result

        return await self.generate_response(result, isCached=isCached)

    async def search_track_metadata(
        self, rawResponse: Optional[ResponseContent] = None
    ):
        """retrieve track metadata based on filter/keyword searches"""
        cacheKey = self._managers.cacheKey.encrypt()
        content = self._responseConfig.content

        if rawResponse is not None:
            content = rawResponse
            cacheKey += CacheKeyQualifier.RAW + "_" + str(rawResponse)

        result = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if result is not None:
            return (
                result
                if rawResponse
                else await self.generate_response(result, isCached=True)
            )

        offset = None
        limit = None
        if rawResponse is None:
            # get counts to either return or determine pagination
            result = await MetadataQueryService(
                self._managers.metadataSession, dataStore=self._dataStore
            ).query_track_metadata(
                self._parameters.assembly,
                self._parameters.get("filter", None),
                self._parameters.get("keyword", None),
                ResponseContent.COUNTS,
            )

            if content == ResponseContent.COUNTS:
                return await self.generate_response(result, isCached=False)

            self._resultSize = result["num_tracks"]
            pageResponse = self.initialize_pagination(raiseError=False)
            if pageResponse:  # will return true if model can be paged and page is valid
                offset = self.offset()
                limit = self._pageSize

        result = await MetadataQueryService(
            self._managers.metadataSession, dataStore=self._dataStore
        ).query_track_metadata(
            self._parameters.assembly,
            self._parameters.get("filter", None),
            self._parameters.get("keyword", None),
            content,
            limit,
            offset,
        )

        if rawResponse is None:
            return await self.generate_response(result, isCached=False)
        else:  # cache the raw response before returning
            await self._managers.cache.set(
                cacheKey, result, namespace=self._managers.cacheKey.namespace
            )
            return result

    async def get_shard(self):
        cacheKey = self._managers.cacheKey.encrypt()

        result = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace
        )

        if result is not None:
            return await self.generate_response(result, isCached=True)

        # TODO: validate track

        # result = await MetadataQueryService(self._managers.metadataSession, self._managers.requestData, self._dataStore) \
        #         .get_shard(self._parameters.track, self._parameters.chr,
        #            responseType=self._responseConfig.content)

        raise NotImplementedError("Query helper not yet implemented")
