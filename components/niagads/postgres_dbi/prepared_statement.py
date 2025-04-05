# generate prepared statements leveraging psycopg2.sql
# TODO - test whether pyscopg2 connection is need to convert to string

from typing import Dict, List, Union

from niagads.enums.core import CaseInsensitiveEnum, auto
from psycopg2.sql import SQL as psSQL
from psycopg2.sql import Identifier as psIdentifier
from psycopg2.sql import Placeholder as psPlaceholder


class Statement(CaseInsensitiveEnum):
    SELECT = auto()
    INSERT = auto()
    UPDATE = auto()


class PreparedStatement:
    """
    leverage pyscopg2 sql package (https://www.psycopg.org/docs/sql.html)
    to generate a prepared statements
    """

    def __init__(self, schemaName, tableName):
        self.__table: str = tableName
        self.__schema: str = schemaName
        self.__useNamedPlaceholders: bool = False
        self.__caseSensitiveNaming: bool = False

    def case_sensitive_naming(self, flag=True):
        """table/schema names are case sensitive"""
        self.__caseSensitiveNaming = flag

    def use_named_placeholders(self, flag=True):
        """
        placholders represented as %(foo)s, instead of %s
        """
        self.__useNamedPlaceholders = flag

    def __format_table_name(self):
        tableName = self.__table if self.__caseSensitiveNaming else self.__table.lower()
        schemaName = (
            self.__schema if self.__caseSensitiveNaming else self.__schema.lower()
        )

        return schemaName, tableName

    def select(self, fields: list, filters: dict, returnAsString: bool = False):
        """
        leverage pyscopg2 sql package (https://www.psycopg.org/docs/sql.html)
        to generate a prepared select statement from a list of fields and dict of field_names:value pairs
        for filtering

        Args:


        Returns:
            prepared insert statement in the format:
                SELECT f1, f2, f3, f4 FROM "schema"."table" WHERE f5 = 'x'

        """
        raise NotImplementedError()

    def insert(self, fields: Union[Dict, List], returnAsString: bool = False):
        """
        leverage pyscopg2 sql package (https://www.psycopg.org/docs/sql.html)
        to generate a prepared insert statement from a dict of field_names:value pairs

        if fields is a dict, field names are sorted; if array, original order is kept

        Args:
            fields (dict|list): list of field names or dict of field_name:value pairs
            returnAsString (bool, optional): flag return as string instead of composed SQL object.   Defaults to False.

        Returns:
            prepared insert statement in the format:
                insert into "schema"."table" ("foo", "bar", "baz") values (%s, %s, %s)
            or, with named placeholders:
                insert into "schema.table" ("foo", "bar", "baz") values (%(foo)s, %(bar)s, %(baz)s)

        """

        fieldNames = fields
        if isinstance(fields, dict):
            fieldNames = list(fields.keys())
            fieldNames.sort()

        # TODO - named placeholders
        if self.__useNamedPlaceholders:
            raise NotImplementedError("TODO - named placeholders")

        formattedPlaceholders = psSQL(", ").join(psPlaceholder() * len(fieldNames))

        schemaName, tableName = self.__format_table_name()
        statement = psSQL(
            "INSERT INTO {table} ({fields}) values ({placeholders})"
        ).format(
            table=psIdentifier(schemaName, tableName),
            fields=psSQL(", ").join(map(psIdentifier, fieldNames)),
            placeholders=formattedPlaceholders,
        )

        # TODO - as string
        if returnAsString:
            raise NotImplementedError("TODO - return as string")
        return statement
