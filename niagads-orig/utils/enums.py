from enum import auto
from strenum import LowercaseStrEnum, UppercaseStrEnum, StrEnum
from re import RegexFlag

class CustomStrEnum:   
    """extension for a `StrEnum` (generic, Lowercase or Uppercase) that includes custom
    class methods for listing and testing enum values

    """
    @classmethod
    def has_value(self, value):
        """ test if the StrEnum contains a value
        currently only works w/StrEnum, LowercaseStrEnum, UppercaseStrEnum"""
        if type(self) == LowercaseStrEnum:
            return value.lower() in self._value2member_map_ 
        elif type(self) == StrEnum:
            return value in self.__value2member_map_
        else:
            return value.upper() in self._value2member_map_ 
        
    @classmethod
    def list(self):
        """ return a list of all values in the StrEnum """
        return [e.value for e in self]
    
    
class ClassProperties(CustomStrEnum, UppercaseStrEnum):
    """enum for functions that extract info about a class -- methods or members?
    """
    METHODS = auto()
    MEMBERS = auto()
    
class ErrorActions(CustomStrEnum, UppercaseStrEnum):
    """enum for possible behaviors on critical errors
    """
    IGNORE = auto()
    FAIL = auto()
    WARN = auto()
    
class RegularExpressions(CustomStrEnum, StrEnum):
    """
    commonly used regexps
    """
    PUBMED_ID = r'^([0-9]{8}|PMID:[0-9]{8})$'
    MD5SUM = r'^[a-fA-F0-9]{32}$'
    DOI = r'(10[.][0-9]{4,}(?:[.][0-9]+)*\/(?:(?!["&\'<>])\S)+)$'
    FILE_SIZE = r'^[.0-9]+\s?(K|M|G)$'
    KEY_VALUE_PAIR = r'^[^\s=]+=[^=;]+$' # key=value

