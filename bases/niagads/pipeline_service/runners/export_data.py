"""Extract and export data from a qualified table to JSON or tab-delimited format."""

import argparse
import asyncio
import json
from enum import auto
from pathlib import Path
from typing import List, Optional

from niagads.arg_parser.core import (
    case_insensitive_enum_type,
    comma_separated_list,
    json_type,
)
from niagads.common.core import ComponentBaseMixin
from niagads.database.genomicsdb.schema.admin.types import TableRef
from niagads.database.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.database.session import DatabaseSessionManager
from niagads.enums.core import CaseInsensitiveEnum
from niagads.settings.core import CustomSettings
from niagads.utils.string import xstr
from sqlalchemy import RowMapping, Select, column, select
from sqlalchemy.exc import NoResultFound


class OutputFormat(CaseInsensitiveEnum):
    """Supported output formats."""

    JSON = auto()
    TAB = auto()
    CSV = auto()

    def get_delimiter(self):
        if self == OutputFormat.TAB:
            return "\t"
        elif self == OutputFormat.CSV:
            return ","
        else:
            raise ValueError("Not delimited format type")


class Settings(CustomSettings):
    """Application settings."""

    DATABASE_URI: str


class DataExporter(ComponentBaseMixin):
    """Extract and export data from database tables."""

    def __init__(
        self,
        database_uri: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize the data exporter.

        Args:
            database_uri (str, optional): PostgreSQL connection URI. If not provided,
                reads from DATABASE_URI environment variable.
            debug (bool): Enable debug logging.
            verbose (bool): Enable verbose output.
        """
        super().__init__(debug=debug, verbose=verbose)

        self.__database_uri = (
            database_uri if database_uri else Settings.from_env().DATABASE_URI
        )
        self.__session_manager = DatabaseSessionManager(self.__database_uri)

        GenomicsDBSchemaBase.register_table_classes()

    def __validate_table_column(self, column: str, table_class):
        if not hasattr(table_class, column):
            raise ValueError(f"Invalid column - `{column}`.")

    def __apply_filters(
        self,
        query: Select,
        table_class: type,
        filters: dict,
    ) -> Select:
        """
        Apply filter conditions to a SQLAlchemy select statement.

        Args:
            query: SQLAlchemy select statement.
            model_class: The ORM model class.
            filters (dict): Dictionary of column_name -> value pairs for filtering.

        Returns:
            SQLAlchemy select statement with filters applied.
        """
        if not filters:
            return query

        for column_name, value in filters.items():
            self.__validate_table_column(column_name, table_class)
            column = getattr(table_class, column_name)
            query = query.where(column == value)

        return query

    def __format_delimited_text(self, data: RowMapping, delimiter: str = "\t") -> str:
        """
        Format data delimited text.

        Args:
            data: RowMapping
            delimiter: str
        Returns:
            str: Tab-delimited formatted string.
        """

        values = [xstr(v, null_str="NULL") for v in data.values()]
        return delimiter.join(values)

    async def export(
        self,
        qualified_table_name: str,
        filters: Optional[dict] = None,
        fields: Optional[list[str]] = None,
    ) -> list[RowMapping]:
        """
        Extract and format data from a table.

        Args:
            qualified_table_name (str): Table name in format 'schema.table'.
            filters (dict, optional): Filter conditions as {column: value}.
            fields (list[str], optional): fields to select

        Returns:
            str: Formatted data as string.

        Raises:
            ValueError: If the table is not found or filters are invalid.
        """
        schema, table = qualified_table_name.split(".")
        table_class = TableRef.get_table_class(schema, table)

        async with self.__session_manager.session_ctx() as session:
            # Build query
            if fields is None:
                stmt = select(table_class)
            else:
                select_columns = []
                for f in fields:
                    self.__validate_table_column(f, table_class)
                    select_columns.append(getattr(table_class, f))
                stmt = select(*select_columns)

            # Apply filters
            stmt = self.__apply_filters(stmt, table_class, filters or {})

            # Execute query
            result = await session.execute(stmt)
            rows = result.mappings().all()

            if rows is None:
                self.logger.warning("No results found.")

            else:
                if self._verbose:
                    self.logger.info(
                        f"Exported {len(rows)} records from '{qualified_table_name}'"
                    )

            return rows

    def __write_to_file(
        self,
        data: list[RowMapping],
        file: str,
        format: OutputFormat = OutputFormat.JSON,
    ):

        with open(file, "w") as fh:
            if format == OutputFormat.JSON:
                fh.write(json.dumps([dict(row) for row in data], indent=2, default=str))
            else:
                print(
                    format.get_delimiter().join(str(h) for h in data[0].keys()), file=fh
                )
            for row in data:
                data_str = self.__format_delimited_text(row, format.get_delimiter())
                print(data_str, file=fh, flush=True)

    async def export_to_file(
        self,
        qualified_table_name: str,
        output_path: str,
        filters: Optional[dict] = None,
        fields: Optional[List[str]] = None,
        output_format: OutputFormat = OutputFormat.JSON,
    ) -> None:
        """
        Extract data and write to file.

        Args:
            qualified_table_name (str): Table name in format 'schema.table'.
            output_path (str): Path where output file will be written.
            filters (dict, optional): Filter conditions as {column: value}.
            fields (list[str]): fields to select
            output_format (OutputFormat): Output format (json or tab).

        Raises:
            ValueError: If output path is invalid.
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        data = await self.export(
            qualified_table_name,
            filters=filters,
            fields=fields,
        )

        if data is not None:
            self.__write_to_file(data, output_file, output_format)


async def main():
    """Entry point for running as a script."""
    parser = argparse.ArgumentParser(
        description="Extract and export data from a database table",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--table",
        metavar="TABLE",
        help="Qualified table name in format 'schema.table'",
    )
    parser.add_argument(
        "--output",
        required=True,
        metavar="FILE",
        help="Output file path",
    )
    parser.add_argument(
        "--format",
        type=case_insensitive_enum_type(OutputFormat),
        default=OutputFormat.TAB,
        help=f"Output format: one of {OutputFormat.list()}",
    )
    parser.add_argument(
        "--filters",
        metavar="JSON",
        type=json_type,
        help='Filter conditions provided as column: value pairs (e.g., \'{"column": "value", ...}\')',
    )
    parser.add_argument(
        "--fields",
        type=comma_separated_list,
        help="comma-separated list of fields to be included in output. If not provided will export all fields",
    )
    # TODO:
    # parser.add_argument(
    #     "--exclude-housekeeping",
    #     type=bool,
    #     action="store_true"
    #     help="exclude housekeeping fields; defaults to True",
    # )
    parser.add_argument(
        "--databaseUri",
        help="PostgreSQL connection URI; if not set, reads DATABASE_URI from environment or .env",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    # Create exporter and run
    exporter = DataExporter(
        database_uri=args.databaseUri,
        debug=args.debug,
        verbose=args.verbose,
    )

    await exporter.export_to_file(
        qualified_table_name=args.table,
        output_path=args.output,
        filters=args.filters,
        fields=args.fields,
        output_format=OutputFormat(args.format),
    )
    print(f"✓ Data successfully exported to {args.output}")


def run_main():
    """Wrapper necessary so that the main coroutine gets correctly awaited."""
    asyncio.run(main())


if __name__ == "__main__":
    run_main()
