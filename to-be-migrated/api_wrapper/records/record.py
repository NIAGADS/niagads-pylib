import logging

from sys import stdout
from multiprocessing import (
    Pool,
)  # note using temporarily to page results b/c paging not yet implemented in API

from .. import make_request, Databases, RecordTypes, FileFormats, PAGE_SIZES
from niagads.utils.string import xstr
from niagads.utils.list import chunker
from niagads.utils.dict import print_dict, get


class RecordParser:
    def __init__(self, database, record=None, debug=False):
        self._debug = debug
        self.logger = logging.getLogger(__name__)
        self._database = self.__validate_database(database)
        self._record = None

        if record is not None:
            self.set_record(record)  # handle error checking

    def __validate_database(self, database):
        db = database.upper()
        if Databases.has_value(db):
            return db
        else:
            raise ValueError(
                "Invalid database: "
                + db
                + "; valid choices are: "
                + xstr(Databases.upper())
            )

    def get(self, attribute, default=None, errorAction="fail"):
        if self._record is None:
            raise TypeError("record is NoneType (not set)")
        else:
            return get(self._record, attribute, default, errorAction)

    def get_record(self):
        return self._record

    def set_record(self, record):
        if record is None:
            raise TypeError("record is NoneType (not set); cannot parse")
        self._record = record

    def get_record_attributes(self):
        if self._record is None:
            raise TypeError("record is NoneType (not set); cannot parse")
        return list(self._record.keys())


class Record:
    def __init__(
        self, recordType, database, requestUrl="https://api.niagads.org", ids=None
    ):
        self._requestUrl = requestUrl
        self._type = self.__validate_type(recordType)
        self._database = None
        self._ids = None
        self._response = None
        self._page_size = 200
        self._response_format = "json"
        self._params = None
        self._nullStr = ""

        self.set_database(database)

        self.logger = logging.getLogger(__name__ + "." + self._type)
        self.logger.info("Record initialized")

    def set_null_str(self, null_str=""):
        """
        set value to be printed for none/null in tabular output

        Args:
            null_str (string): usually one of '', NA, N/A, NULL. Defaults to '' (empty string).
        """
        self._nullStr = null_str

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
        if FileFormats.has_value(format.upper()):
            return format.upper()
        else:
            raise ValueError(
                "Invalid format: "
                + format
                + "; valid choices are: "
                + xstr(FileFormats.list())
            )

    def get_page_size(self):
        return self._page_size

    def set_page_size(self, size):
        self._page_size = self.__validate_page_size(size)

    def __validate_page_size(self, size):
        if size > max(PAGE_SIZES):
            raise ValueError(
                "Page size must be set to a value <= "
                + max(PAGE_SIZES)
                + "; recommend choices: "
                + xstr(PAGE_SIZES)
            )
        else:
            return size

    def get_database(self):
        return self._database

    def set_database(self, database):
        self._database = self.__validate_database(database)

    def __validate_database(self, database):
        if Databases.has_value(database.upper()):
            if Databases[database.upper()] != Databases.GENOMICS:
                raise NotImplementedError(
                    "API Wrapper currently only written for `GENOMICS` [GenomicsDB] lookups"
                )
            return database.upper()
        else:
            raise ValueError(
                "Invalid database: "
                + database
                + "; valid choices are: "
                + xstr(Databases.list())
            )

    def get_type(self):
        return self._type

    def __validate_type(self, recordType):
        if RecordTypes.has_value(recordType.upper()):
            return recordType.upper()
        else:
            raise ValueError(
                "Invalid record type: "
                + recordType
                + "; valid choices are: "
                + xstr(RecordTypes.list())
            )

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

    def _fetch_chunk(self, ids):
        idParam = {"id": xstr(ids)}
        params = idParam if self._params is None else {**idParam, **self._params}
        endpoint = self._database.lower() + "/" + self._type.lower() + "/"
        return make_request(self._requestUrl, endpoint, params)

    def fetch(self):
        if self._page_size is None:
            raise ValueError("Must set page size before fetching")
        chunks = chunker(self._ids, self._page_size, returnIterator=True)
        with Pool() as pool:
            response = pool.map(self._fetch_chunk, chunks)
            self._response = sum(response, [])  # concatenates indvidual responses

    def write_response(self, file=stdout, format=None):
        if format is None:
            format = self._response_format
        if format.upper() == FileFormats.JSON:
            # use get_response b/c it does the None check
            return print(print_dict(self.get_response(), pretty=True), file=file)
        else:
            # other format types need to be overloaded in subclasses
            return NotImplementedError(
                format
                + "formatted output not yet implemented for record type "
                + self._type
            )
