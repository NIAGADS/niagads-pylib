import json
import logging
from .string import xstr

class RestrictedValueError(Exception):
    """Exception raised when controlled value does not match reference enum
    assumes the "Enum" is a "CustomStrEnum" which has a .list() class member
    Attributes:
        label (str) -- description of field / attribute / paramter being matched (e.g., record, database)
        value (str | number) -- value being matched
        enum (enum) -- enum containing allowable values
    """

    def __init__(self, label, value, enum):  
        self.__message = "Invalid value for " + label \
            + ": " + xstr(value) \
            + "; valid values are: " + xstr(enum.list())
        super().__init__(json.dumps(self.__message))






