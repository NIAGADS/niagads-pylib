from fastapi.exceptions import RequestValidationError

from sqlmodel import text
from sqlalchemy.exc import NoResultFound

from api.common.enums import CacheKeyQualifier, ResponseContent, CacheNamespace
from api.common.helpers import Parameters, ResponseConfiguration, RouteHelper, PaginationCursor
from api.common.types import Range
from api.models.response_model_properties import CacheKeyDataModel, QueryDefinition

from .constants import CACHEDB_PARALLEL_TIMEOUT
from ..dependencies.parameters import InternalRequestParameters



class GenomicsRouteHelper(RouteHelper):  
    
    def __init__(self, managers: InternalRequestParameters, 
        responseConfig: ResponseConfiguration,
        params: Parameters,
        query: QueryDefinition
    ):
        super().__init__(managers, responseConfig, params)
        self.__query = query
        self.__idParameter: str = 'id'
    

    async def __run_query(self): 
        # TODO: add limit & offset
        # TODO: counts, summary, ids, urls response contents
        
        statement = text(self.__query.query)
                
        try:
            if len(self.__query.bindParameters) > 0: 
                parameters = { param : 
                    self._parameters.get(self.__idParameter) if param == 'id' else self._parameters.get(param)  
                    for param in self.__query.bindParameters 
                }
                # .mappings() returns result as dict
                result = (await self._managers.session.execute(statement, parameters)).mappings().all()
            else:
                result = (await self._managers.session.execute(statement, parameters)).mappings().all()
            
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

        
    async def run_query(self):
        cacheKey = self._managers.cacheKey.encrypt()

        result = await self._managers.cache.get(
            cacheKey, namespace=self._managers.cacheKey.namespace)
        
        if result is not None:
            return await self.generate_response(result, True)
        
        result = await self.__run_query()
        
        return await self.generate_response(result, False)
