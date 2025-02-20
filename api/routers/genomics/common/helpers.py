from fastapi.exceptions import RequestValidationError

from sqlmodel import bindparam, text
from sqlalchemy.exc import NoResultFound

from niagads.utils.dict import all_values_are_none

from api.common.helpers import Parameters, ResponseConfiguration, RouteHelper, PaginationCursor
from api.models.query_defintion import QueryDefinition

from api.routers.genomics.common.constants import CACHEDB_PARALLEL_TIMEOUT
from api.routers.genomics.dependencies.parameters import InternalRequestParameters
from api.routers.genomics.models.feature_score import GWASSumStatResponse, QTLResponse
from api.routers.genomics.models.genomics_track import GenomicsTrack
from api.routers.genomics.queries.track_data import TrackGWASSumStatQuery, TrackQTLQuery

class GenomicsRouteHelper(RouteHelper):  
    
    def __init__(self, managers: InternalRequestParameters, 
        responseConfig: ResponseConfiguration,
        params: Parameters,
        query: QueryDefinition,
        idParameter: str = 'id'
    ):
        super().__init__(managers, responseConfig, params)
        self.__query = query
        self.__idParameter: str = idParameter
    
    
    async def __run_query(self): 
        statement = text(self.__query.query)

        try:
            if self.__query.bindParameters is not None: 
                # using the binparam object allows us to use the same parameter multiple times
                # which is not possible w/simple dict representaion
                parameters = [bindparam(param,
                    self._parameters.get(self.__idParameter) \
                    if param == 'id' else self._parameters.get(param)) \
                        for param in self.__query.bindParameters]

                # .mappings() returns result as dict
                result = (await self._managers.session.execute(statement.bindparams(*parameters))).mappings().all()
            else:
                result = (await self._managers.session.execute(statement)).mappings().all()
            
            if len(result) == 0: 
                raise NoResultFound()
            
            if all_values_are_none(result[0]):
                raise NoResultFound()
            
            if self.__query.fetchOne:
                return result[0]
            else:
                return result
        
        except NoResultFound as e:
            if self.__query.errorOnNull is not None:
                raise RequestValidationError(self.__query.errorOnNull)
            elif self.__query.fetchOne:
                return {}
            else:
                return []


    async def get_query_response(self):
        cachedResponse = await self._get_cached_response()
        if cachedResponse is not None:
            return cachedResponse
        
        result = await self.__run_query()
        
        return await self.generate_response(result, False)
    
    
    async def get_track_data_query_response(self):
        cachedResponse = await self._get_cached_response()
        if cachedResponse is not None:
            return cachedResponse
        
        result: GenomicsTrack = await self.__run_query()
        
        match result.data_category:
            case 'QTL':
                self.__query = TrackQTLQuery
                self._responseConfig.model = QTLResponse
            case _ if result.data_category.startswith('GWAS'):
                self.__query = TrackGWASSumStatQuery
                self._responseConfig.model = GWASSumStatResponse
            case _:
                raise RuntimeError(f'Track with invalid type retrieved: {result.track_id} - {result.data_category}')
        
        return self.get_query_response()

