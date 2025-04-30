from typing import Optional
from fastapi.exceptions import RequestValidationError

from pydantic import BaseModel
from sqlalchemy import RowMapping
from sqlmodel import bindparam, func, select, text
from sqlalchemy.exc import NoResultFound

from niagads.utils.dict import all_values_are_none

from api.common.enums.database import DataStore
from api.common.enums.response_properties import ResponseContent, ResponseView
from api.common.helpers import Parameters, ResponseConfiguration, MetadataRouteHelper
from api.common.services.metadata_query import MetadataQueryService
from api.common.types import Range
from api.config.settings import Settings
from api.models.query_defintion import QueryDefinition

from api.routes.genomics.common.constants import (
    CACHEDB_PARALLEL_TIMEOUT,
    DEFAULT_PAGE_SIZE,
)
from api.routes.genomics.dependencies.parameters import InternalRequestParameters
from api.routes.genomics.models.feature_score import GWASSumStatResponse, QTLResponse
from api.routes.genomics.models.genomics_track import GenomicsTrack
from api.routes.genomics.queries.track_data import (
    TrackGWASSumStatQuery,
    TrackQTLGeneQuery,
)


class QueryOptions(BaseModel):
    fetchOne: Optional[bool] = False
    countsOnly: Optional[bool] = False
    rawResponse: Optional[bool] = False
    range: Optional[Range] = None


class GenomicsRouteHelper(MetadataRouteHelper):

    def __init__(
        self,
        managers: InternalRequestParameters,
        responseConfig: ResponseConfiguration,
        params: Parameters,
        query: QueryDefinition = None,
        idParameter: str = "id",
    ):
        super().__init__(
            managers, responseConfig, params, [DataStore.SHARED, DataStore.GENOMICS]
        )
        self.__query = query
        self.__idParameter: str = idParameter

    def __build_counts_statement(self):
        if self.__query.countsQuery != None:
            statement = text(self.__query.countsQuery)
            parameters = [bindparam("id", self._parameters.get(self.__idParameter))]
            statement = statement.bindparams(*parameters)
        else:
            statement = text(
                f"SELECT count(*) AS result_size FROM ({self.__query.query}) r"
            )
            parameters = [
                bindparam(
                    param,
                    (
                        self._parameters.get(self.__idParameter)
                        if param == "id"
                        else self._parameters.get(param)
                    ),
                )
                for param in self.__query.bindParameters
            ]

            statement = statement.bindparams(*parameters)

        return statement

    def __build_statement(self, opts: QueryOptions):
        if opts.countsOnly:
            statement = self.__build_counts_statement()
        else:
            query = self.__query.query
            if opts.range is not None:
                if "rank_start" not in self.__query.bindParameters:
                    query += f" LIMIT {self._pageSize}"
                    query += f" OFFSET {opts.range.end}"

            statement = text(query)

            if self.__query.bindParameters is not None:
                # using the binparam object allows us to use the same parameter multiple times
                # which is not possible w/simple dict representaion
                parameters = []
                for param in self.__query.bindParameters:
                    if param == "id":
                        parameters.append(
                            bindparam(param, self._parameters.get(self.__idParameter))
                        )
                    elif param == "rank_start":
                        parameters.append(
                            bindparam(
                                param, 0 if opts.range is None else opts.range.start
                            )
                        )
                    elif param == "rank_end":
                        parameters.append(
                            bindparam(
                                param,
                                (
                                    self._pageSize - 1
                                    if opts.range is None
                                    else opts.range.end
                                ),
                            )
                        )
                    else:
                        parameters.append(bindparam(param, self._parameters.get(param)))

                statement = statement.bindparams(*parameters)

        return statement

    async def __run_query(self, opts: QueryOptions):
        statement = self.__build_statement(opts)
        try:
            # .mappings() returns result as dict
            result = (await self._managers.session.execute(statement)).mappings().all()

            if len(result) == 0:
                raise NoResultFound()

            if all_values_are_none(result[0]):
                raise NoResultFound()

            if self.__query.fetchOne or opts.fetchOne or opts.countsOnly:
                return result[0]
            else:
                return result

        except NoResultFound as e:
            if self.__query.errorOnNull is not None:
                raise RequestValidationError(self.__query.errorOnNull)
            if self.__query.fetchOne:
                return {}
            else:
                return []

    async def __get_paged_query_response(self):
        rSize = await self.__run_query(QueryOptions(countsOnly=True))
        self._resultSize = rSize["result_size"]
        self.initialize_pagination()
        return await self.get_query_response(
            QueryOptions(range=self.slice_result_by_page())
        )

        """"
        pRange = self.slice_result_by_page()
        if self._responseConfig.view == ResponseView.TABLE:
            if self._resultSize > self._pageSize:
                if self.__query.messageOnResultSize is not None:
                    currentPage = self.page()
                    query = f'{Settings.get().API_PUBLIC_URL}{self._managers.requestData.endpoint}?page={currentPage}'
                    rangeMessage =  f'top {self._pageSize} results'if currentPage == 1 else f'results [{pRange.start + 1}, {pRange.end}]'
                    message = self.__query.messageOnResultSize.format(self._resultSize, rangeMessage, query)
        """

    async def get_query_response(self, opts: QueryOptions = QueryOptions()):
        # fetchCounts ->  get counts only
        cachedResponse = await self._get_cached_response()
        if cachedResponse is not None:
            return cachedResponse

        result = await self.__run_query(opts)

        if opts.rawResponse:
            return result

        return await self.generate_response(result, False)

    async def __validate_track(self):
        result = await MetadataQueryService(
            self._managers.session, dataStore=self._dataStore
        ).get_track_metadata(tracks=[self._parameters.track])
        if len(result) == 0:
            raise RequestValidationError(
                "Track not found in the NIAGADS Alzheimer's GenomicsDB"
            )

        return result[0]

    async def get_track_data_query_response(self):
        cachedResponse = await self._get_cached_response()
        if cachedResponse is not None:
            return cachedResponse

        # this will both validate and allow us to determine which kind of track
        result: GenomicsTrack = await self.__validate_track()
        # result: GenomicsTrack = await self.__run_query(QueryOptions(fetchOne=True))

        match result.data_category:
            case "QTL":
                self.__query = TrackQTLGeneQuery
                if self._responseConfig.content == ResponseContent.FULL:
                    self._responseConfig.model = QTLResponse
            case _ if result.data_category.startswith("GWAS"):
                self.__query = TrackGWASSumStatQuery
                if self._responseConfig.content == ResponseContent.FULL:
                    self._responseConfig.model = GWASSumStatResponse
            case _:
                raise RuntimeError(
                    f"Track with invalid type retrieved: {result.track_id} - {result.data_category}"
                )

        match self._responseConfig.content:
            case ResponseContent.SUMMARY | ResponseContent.COUNTS:
                counts = await self.get_query_response(
                    QueryOptions(countsOnly=True, rawResponse=True)
                )
                suffix = (
                    "qtls"
                    if result.data_category == "QTL"
                    else "significant_associations"
                )
                if self._responseConfig.content == ResponseContent.COUNTS:
                    return await self.generate_response(
                        {f"num_{suffix}": counts["result_size"]}
                    )
                else:
                    result[f"num_{suffix}"] = counts["result_size"]
                    return await self.generate_response(result)
            case _:  # FULL
                return await self.__get_paged_query_response()
                # return await self.get_query_response()
