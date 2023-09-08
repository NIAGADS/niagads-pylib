import logging

from sys import stdout
from multiprocessing import Pool # note using temporarily to page results b/c paging not yet implemented in API

from niagads.api_wrapper import constants, make_request
from niagads.utils.string_utils import xstr
from niagads.utils.array_utils import chunker
from niagads.utils.sys_utils import print_dict

class Record:
    def __init__(self, recordType, database, requestUrl="https://api.niagads.org", ids=None):
        self._requestUrl = requestUrl
        self._type = None
        self._database = None
        self._ids = None 
        self._response = None
        self._page_size = 200
        self._response_format = 'json'
        self._params = None
        
        self.__validate_type(recordType)
        self.set_database(database)
        
        self._logger = logging.getLogger(__name__ + self._type)


    def get_response(self):
        if self._response is None:
            raise TypeError("`response` is NoneType; did you `run()` the lookup?")
        return self._response

    def get_response_format(self):
        return self._response_format
        
    def set_response_format(self, format):
        self._response_format = self._validate_response_format(format)
    
    def _validate_response_format(self, format):
        # set as protected b/c may need to be overloaded
        # not 100% on how this will work
        if format not in constants.FORMATS:
            raise ValueError("Invalid format: " + format
                + "; valid choices are: " + xstr(constants.FORMATS))
        else:
            return format
    
    def get_page_size(self):
        return self._page_size
    
    def set_page_size(self, size):
        self._page_size = self.__validate_page_size(size)
    
    def __validate_page_size(self, size):
        if size > max(constants.PAGES):
            raise ValueError("Page size must be set to a value <= " + max(constants.PAGES)
                + "; recommend choices: " + xstr(constants.PAGES))
        else:
            self._page_size = size        
    
    def get_database(self):
        return self._database
    
    def set_database(self, database):
        self._database = self.__validate_database(database)
    
    def __validate_database(self, database):
        if database not in constants.DATABASES:
            raise ValueError("Invalid database: " + database
                + "; valid choices are: " + xstr(constants.DATABASES))
        else:
            return database
        
    def get_type(self):
        return self._type
    
    def __validate_type(self, recordType):
        if recordType not in constants.RECORD_TYPES:
            raise ValueError("Invalid record type: " + recordType
                + "; valid choices are: " + xstr(constants.RECORD_TYPES))
        else:
            return recordType
        
    def set_request_url(self, url):
        self._requestUrl = url
        
    def get_request_url(self):
        return self._requestUrl
    
    def set_ids(self, ids):
        # this function may need to be overloaded
        # e.g., see variant.py
        self._ids = ids
    
    def get_ids(self, returnStr=False):
        return self._ids if not returnStr else xstr(self._ids)
    
    def get_query_size(self):
        return 0 if self._ids is None else len(self._ids)
    
    def set_params(self, params):
        self._params = params
        
    def get_params(self):
        return self._params
    
    def __lookup(self, ids):
        idParam = { "id": xstr(ids)}
        params = idParam if self._params is None else {**idParam, **self._params}
        endpoint = self._database + '/' + self._type + '/'       
        make_request(endpoint, params)

    def run(self):
        chunks = chunker(self._ids, self._page_size)      
        with Pool() as pool:
            response = pool.map(self.__lookup, chunks)
            self._response = sum(response, []) # concatenates indvidual responses
    
    def write_response(self, file=stdout, format=None):
        if format is None:
            format = self._response_format
        if format == 'json':
            # use get_response b/c it does the None check
            return print(print_dict(self.get_response(), pretty=True), file=file)
        else:
            # other format types need to be overloaded in subclasses
            return NotImplementedError(format + "formatted output not yet implemented for record type " + self._type)
