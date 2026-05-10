from datetime import datetime
import gzip
import json
from typing import Any

from dateutil import parser
from niagads.common.models.types import Range
from sqlalchemy import LargeBinary
from sqlalchemy.dialects.postgresql import INT4RANGE
from sqlalchemy.types import DateTime, TypeDecorator
from asyncpg import Range as AsyncPGRange


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
        # return value.bracket_notation()

        return AsyncPGRange(
            lower=value.start,
            upper=value.end,
            upper_inc=value.inclusive_end,
        )

    def process_result_value(self, value: AsyncPGRange, dialect):
        """
        Convert a PostgreSQL INT4RANGE back to a Range object.
        called automatically when result is fetched
        Args:
            value (str): The PostgreSQL range string.
            dialect: The database dialect in use.
        Returns:
            Range: The reconstructed Range object or None.
        """
        if value is None:
            return None
        return Range(
            start=value.lower,
            end=value.upper,
            inclusive_end=value.upper_inc,
        )


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


class CompressedJson(TypeDecorator):
    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> bytes | None:
        if value is None:
            return None

        json_bytes = json.dumps(value, separators=(",", ":")).encode("utf-8")
        return gzip.compress(json_bytes)

    def process_result_value(self, value: bytes | None, dialect) -> Any:
        if value is None:
            return None

        json_bytes = gzip.decompress(value)
        return json.loads(json_bytes.decode("utf-8"))
