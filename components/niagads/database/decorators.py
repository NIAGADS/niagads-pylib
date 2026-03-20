from datetime import datetime

from dateutil import parser
from niagads.common.models.types import Range
from sqlalchemy.dialects.postgresql import INT4RANGE
from sqlalchemy.types import DateTime, TypeDecorator


class RangeType(TypeDecorator):
    """
    Custom SQLAlchemy type for converting a Range object to and from PostgreSQL INT4RANGE.
    Uses the Range.to_bracket_string() method for serialization and parses the string for deserialization.
    """

    impl = INT4RANGE
    cache_ok = True
    
    def process_bind_param(self, value: Range, dialect):
        """
        Convert a Range object to PostgreSQL INT4RANGE string format for storage.
        called automatically at statement execution
        Args:
            value (Range): The Range object to convert.
            dialect: The database dialect in use.
        Returns:
            str: PostgreSQL range string or None.
        """
        if value is None:
            return None
        # Use the Range class's to_bracket_string method
        # sets inclusize end to True b/c most of the time dealing
        # with 1-based genomic coordinates
        return value.to_bracketed_string()

    def process_result_value(self, value, dialect):
        """
        Convert a PostgreSQL INT4RANGE string back to a Range object.
        called automatically when result is fetched
        Args:
            value (str): The PostgreSQL range string.
            dialect: The database dialect in use.
        Returns:
            Range: The reconstructed Range object or None.
        """
        if value is None:
            return None
        # Parse the PostgreSQL range string back to a Range object
        # Example: '[1,100)' -> Range(start=1, end=100)
        import re

        match = re.match(r"\[(\d+),\s*(\d+)([\]\)])", value)
        if match:
            inclusiveEnd = True
            start = int(match.group(1))
            end = int(match.group(2))
            bracket = match.group(3)
            if bracket == ")":
                end -= 1  # exclusive end, so subtract 1
                inclusiveEnd = False
            return Range(start=start, end=end, inclusive_end=inclusiveEnd)
        return value


class AutoDateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None or isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return parser.parse(value)
            except (ValueError, TypeError) as e:
                raise ValueError(f"Could not parse datetime string: {value}") from e
        raise TypeError(f"Expected datetime or str, got {type(value)}")
