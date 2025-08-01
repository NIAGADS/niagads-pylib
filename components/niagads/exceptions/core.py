from enum import auto
import json

from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.string import xstr


def extract_exception_message(ex: Exception) -> None:
    """returns last line of stack trace"""
    return "{0}: {1}".format(ex.__class__.__name__, ex)


class ErrorActions(CaseInsensitiveEnum):
    """enum for possible behaviors on critical errors"""

    IGNORE = auto()
    FAIL = auto()
    WARN = auto()


class AbstractMethodNotImplemented(NotImplementedError):
    def __init__(self, methodName):
        self.message = (
            "Abstract `"
            + methodName
            + "` method has not been implemented for this child class"
        )
        super().__init__(self.message)


class IllegalArgumentError(ValueError):
    pass


class RestrictedValueError(Exception):
    """Exception raised when controlled value does not match reference enum
    assumes the "Enum" is a "CaseInsensitiveEnum" which has a .list() class member
    Attributes:
        label (str) -- description of field / attribute / paramter being matched (e.g., record, database)
        value (str | number) -- value being matched
        enum (enum) -- enum containing allowable values
    """

    def __init__(self, label, value, enum: CaseInsensitiveEnum):
        self.message = (
            "Invalid value for "
            + label
            + ": "
            + xstr(value)
            + "; valid values are: "
            + xstr(enum.list())
        )

        super().__init__(json.dumps(self.message))


class ValidationError(Exception):
    """
    Generic ValidationException (raise when validation fails)
    """

    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class TimerError(Exception):
    """A custom exception used to report errors in use of Timer class"""


class ParserError(Exception):
    """
    custom exception to report errors in parsing
    """

    def __init__(self, message, errors):
        super().__init__(message)
        self.errors = errors
