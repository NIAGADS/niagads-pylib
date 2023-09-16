from enum import auto
from strenum import LowercaseStrEnum, UppercaseStrEnum, StrEnum

class CustomStrEnum:   
    @classmethod
    def has_value(self, value):
        """ currently only works w/StrEnum, LowercaseStrEnum, UppercaseStrEnum"""
        if type(self) == LowercaseStrEnum:
            return value.lower() in self._value2member_map_ 
        else:
            return value.upper() in self._value2member_map_ 
        
    @classmethod
    def list(self):
        return [e.value for e in self]
    

class CLASS_PROPERTIES(CustomStrEnum, UppercaseStrEnum):
    METHODS=auto()
    MEMBERS=auto()
    
class ERROR_ACTIONS(CustomStrEnum, UppercaseStrEnum):
    IGNORE=auto()
    FAIL=auto()
    WARN=auto()