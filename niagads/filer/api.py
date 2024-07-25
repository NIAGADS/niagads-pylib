import logging
import requests
from urllib.parse import urlencode

from ..utils.dict import print_dict

# TODO - validate endpoints against VALID_FILER_ENDPOINTS
# TODO - validate genome builds against SUPPORTED_GENOME_BUILDS
# TODO - FILTERS/validate filters against FILER_TRACK_FILTERS

DEFAULT_REQUEST_URI = 'https://tf.lisanwanglab.org/FILER'

SUPPORTED_GENOME_BUILDS = ["GRCh37", "GRCh38", "grch38", "grch37", "hg38", "hg19"]
VALID_FILER_ENDPOINTS = []

FILER_TRACK_FILTERS = {
    "dataSource": "original data source ", 
    "assay": "assay type", 
    "featureType": "feature type", 
    "antibodyTarget": "target of ChIP-seq or other immunoprecipitation assay",
    "project": "member of a collection of related tracks, often an ENCODE project",
    "tissue": "tissue associated with biosample"
}


class FILERApiWrapper():
    """ Wrapper functions for FILER API, to help standardize, validate calls and protect from attacks """
    
    def __init__(self, requestUri: str, debug=False):
        self.logger = logging.getLogger(__name__)
        self._debug = debug
        self.__filerRequestUri = DEFAULT_REQUEST_URI if requestUri is None else requestUri
        

    def map_genome_build(self, genomeBuild: str):
        ''' return genome build in format filer expects '''
        if '38' in genomeBuild:
            return 'hg38'
        if genomeBuild == 'GRCh37':
            return 'hg19'
        return genomeBuild

# ?trackIDs=NGEN000611,NGEN000615,NGEN000650&region=chr1:50000-1500000

    def __map_request_params(self, params:dict):
        ''' map request params to format expected by FILER'''
        # genome build
        newParams = {"outputFormat": "json"}
        if 'assembly' in params:
            newParams['genomeBuild'] = self.map_genome_build(params['assembly'])

        if 'genomeBuild' in params:
            newParams['genomeBuild'] = self.map_genome_build(params['genomeBuild'])

        if 'id' in params:
            newParams['trackIDs'] = params['id']

        if 'track_id' in params:
            # key = "trackIDs" if ',' in params['track_id'] else "trackID"
            newParams['trackIDs'] = params['track_id']
            
        if 'span' in params:
            newParams['region'] = params['span']

        return newParams


    # TODO: error checking
    def make_request(self, endpoint:str, params: dict, returnSuccess=False):
        ''' map request params and submit to FILER API'''
        requestParams = self.__map_request_params(params)
        requestUrl = self.__filerRequestUri + "/" + endpoint + ".php?" + urlencode(requestParams)
        try:
            response = requests.get(requestUrl)
            response.raise_for_status()     
            if self._debug:
                self.logger.debug("SUCCESS: " + str(len(response.json()))) 
            if returnSuccess:
                return True    
            return response.json()
        except requests.JSONDecodeError as err:
            raise LookupError(f'Unable to parse FILER repsonse `{response.content}` for the following request: {requestUrl}')
        except requests.exceptions.HTTPError as err:
            if self._debug:
                self.logger.debug("HTTP Request FAILED")
            if returnSuccess:
                return False
            return {"message": "Error accessing FILER: " + err.args[0]}

