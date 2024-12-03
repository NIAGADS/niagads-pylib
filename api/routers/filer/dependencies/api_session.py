from aiohttp import ClientSession
from aiohttp.connector import TCPConnector

from api.common.enums import Assembly
from api.config.settings import get_settings

from ..common.enums import FILERApiEndpoint


class FILERApiWrapper():
    """
    """

    def __map_genome_build(self, assembly: Assembly):
        ''' return genome build value FILER expects '''
        return 'hg19' if assembly == Assembly.GRCh37 \
            else 'hg38'

    def __build_request_params(self, parameters: dict):
        ''' map request params to format expected by FILER'''
        requestParams = {'outputFormat': 'json'}
        
        if 'assembly' in parameters:
            requestParams['genomeBuild'] = self.__map_genome_build(parameters['assembly'])

        if 'track' in parameters:
            # key = "trackIDs" if ',' in params['track_id'] else "trackID"
            requestParams['trackIDs'] = parameters['track']
            
        if 'span' in parameters:
            requestParams['region'] = parameters['span']

        return requestParams

    async def fetch(self, endpoint: FILERApiEndpoint, params: dict):
        ''' map request params and submit to FILER API'''
        try:
            requestParams = self.__build_request_params(params)

            async with self.__session.get(str(endpoint), params=requestParams) as response:
                result = await response.json() 
            return result
        except Exception as e:
            raise LookupError(f'Unable to parse FILER response `{response.content}` for the following request: {str(response.url)}')
    
    # TODO parallel fetch
