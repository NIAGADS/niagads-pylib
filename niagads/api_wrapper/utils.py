import requests
import logging
import json
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
            raise ResponseError(rJson)
        else:
            return response.json()
    except ResponseError as err:
        LOGGER.error("NIAGADS API returned an error: " + requestUrl, err, stack_info=True, exec_info=True)
    except requests.exceptions.HTTPError as err:
        LOGGER.error("HTTP Error: " + requestUrl, err, stack_info=True, exc_info=True)
        raise err
    except requests.exceptions.JSONDecodeError as err:
        log_JSON_error(requestUrl, response, err)
        raise err
    except requests.exceptions.InvalidJSONError as err:
        log_JSON_error(requestUrl, response, err)
        raise err
  
    
def log_JSON_error(requestUrl, response, error):
    """
    logs JSON error

    Args:
        requestUrl (string): request URL
        response (obj): response object
        error (obj): error object
    """
    LOGGER.error("Invalid JSON reponse: " + requestUrl)
    LOGGER.error(response.content)
    LOGGER.error(error, stack_info=True, exc_info=True)

class ResponseError(Exception):
    """Exception raised for successful API requests that return error messages.

    Attributes:
        requestUri -- request made
        response -- JSON response containing error message
    """

    def __init__(self, message):
        self.__message = message
        super().__init__(json.dumps(self.__message))
