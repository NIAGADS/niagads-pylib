import requests
from urllib.parse import urlencode
from copy import deepcopy

from shared_resources import constants


def __genome_build(genomeBuild):
    ''' return genome build in format filer expects '''
    if '38' in genomeBuild:
        return 'hg38'
    if genomeBuild == 'GRCh37':
        return 'hg19'
    return genomeBuild

# ?trackIDs=NGEN000611,NGEN000615,NGEN000650&region=chr1:50000-1500000

def __map_request_params(params):
    ''' map request params to format expected by FILER'''
    # genome build
    newParams = {"outputFormat": "json"}
    if 'assembly' in params:
        newParams['genomeBuild'] = __genome_build(params['assembly'])

    if 'genomeBuild' in params:
        newParams['genomeBuild'] = __genome_build(params['genomeBuild'])

    if 'id' in params:
        key = "trackIDs" if ',' in params['id'] else "trackID"
        newParams[key] = params['id']

    if 'span' in params:
        newParams['region'] = params['span']
   
    return newParams


# TODO: error checking
def make_request(endpoint, params, returnSuccess=False):
    ''' map request params and submit to FILER API'''
    requestParams = __map_request_params(params)
    requestUrl = constants.URLS.filer_api + "/" + endpoint + ".php?" + urlencode(requestParams)
    try:
        response = requests.get(requestUrl)
        response.raise_for_status()      
        if returnSuccess:
            return True       
        return response.json()
    except requests.exceptions.HTTPError as err:
        if returnSuccess:
            return False
        return {"message": "Error accessing FILER: " + err.args[0]}

