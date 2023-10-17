from enum import auto
from strenum import LowercaseStrEnum, UppercaseStrEnum

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
        else:
            return value.upper() in self._value2member_map_ 
        
    @classmethod
    def list(self):
        """ return a list of all values in the StrEnum """
        return [e.value for e in self]
    
    

class CLASS_PROPERTIES(CustomStrEnum, UppercaseStrEnum):
    """enum for functions that extract info about a class -- methods or members?
    """
    METHODS=auto()
    MEMBERS=auto()
    
class ERROR_ACTIONS(CustomStrEnum, UppercaseStrEnum):
    """enum for possible behaviors on critical errors
    """
    IGNORE=auto()
    FAIL=auto()
    WARN=auto()