from enum import StrEnum, auto, Enum
from fastapi.exceptions import RequestValidationError

from api.common.formatters import clean, print_enum_values

class CaseInsensitiveEnum(StrEnum):
    # after from https://stackoverflow.com/a/76131490
    @classmethod
    def _missing_(cls, value: str): # allow to be case insensitive
        for member in cls:
            if member.value.lower() == value.lower(): 
                return member
    
        raise KeyError(value)
    
class EnumParameter(CaseInsensitiveEnum):
    @classmethod
    def exclude(cls, name, exclude):
        return EnumParameter(name, { member.name: member.value for member in cls if member not in exclude })

    @classmethod
    def get_description(cls):
        return f'One of: {print_enum_values(cls)}.'
    
    @classmethod
    def validate(cls, value, label: str, returnCls: Enum):
        try:
            cls(clean(value))
            return returnCls(value)
        except:
            raise RequestValidationError(f'Invalid value provided for `{label}`: {value}.  Allowable values for this query are: {print_enum_values(cls)}' )



