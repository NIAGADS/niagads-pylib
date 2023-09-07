import requests
import logging
from sys import exit
from urllib.parse import urlencode

LOGGER = logging.getLogger(__name__)

def make_request(requestUri, endpoint, params):
    """
    wrapper to build and make a request against the NIAGADS API
    includes error check

    Args:
        requestUri (string): base url for the api
        endpoint (string): endpoint to be queried
        params (dict): dict of param_name:value pairs

    Raises:
        requests.exceptions.HTTPError

    Returns:
        JSON response if successful
    """
    requestUrl = requestUri + "/" + endpoint 
    if params is not None:
        requestUrl += '?' + urlencode(params)
    try:
        response = requests.get(requestUrl)
        response.raise_for_status()
        rJson = response.json() 
        if 'message'  in rJson:
            raise requests.exceptions.InvalidURL
        else:
            return response.json()
    except requests.exceptions.InvalidURL:
        LOGGER.error("API returnd an error: " + requestUrl, rJson)
    except requests.exceptions.HTTPError as err:
        LOGGER.error("HTTP Error: " + requestUrl, err, stack_info=True, exc_info=True)
        raise err
    except requests.exceptions.InvalidJSONError as err:
        LOGGER.error("Invalid JSON reponse: " + requestUrl, err, stack_info=True, exc_info=True)
        raise err
        
        