"""Utility functions for extracting schema and table information from SQLAlchemy models"""

from typing import Dict, List

from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import DeclarativeBase


def get_available_schemas() -> List[str]:
    """
    Get list of all registered schema names from SchemaRegistry.

    Returns:
        List[str]: List of schema names in uppercase
    """
    return sorted(list(SchemaRegistry._registry.keys()))


def get_schema_tables(schema_name: str) -> List[str]:
    """
    Get list of all table names for a given schema.

    Args:
        schema_name (str): Name of the schema (case-insensitive)

    Returns:
        List[str]: List of table names in the schema

    Raises:
        KeyError: If schema_name is not registered
    """
    schema_base: DeclarativeBase = SchemaRegistry.get_schema_base(schema_name)
    metadata: MetaData = schema_base.metadata

    # Extract table names from metadata
    table_names = [table.name for table in metadata.sorted_tables]
    return sorted(table_names)


def get_table_info(schema_name: str, table_name: str) -> Dict:
    """
    Get detailed information about a specific table including columns.

    Args:
        schema_name (str): Name of the schema (case-insensitive)
        table_name (str): Name of the table

    Returns:
        Dict: Dictionary containing table information including:
            - schema: Schema name
            - table: Table name
            - columns: List of column names
            - has_run_id: Boolean indicating if table has run_id column

    Raises:
        KeyError: If schema or table not found
    """
    schema_base: DeclarativeBase = SchemaRegistry.get_schema_base(schema_name)
    metadata: MetaData = schema_base.metadata

    # Find the table in metadata
    table: Table = None
    for tbl in metadata.sorted_tables:
        if tbl.name == table_name:
            table = tbl
            break

    if table is None:
        raise KeyError(f"Table '{table_name}' not found in schema '{schema_name}'")

    # Extract column information
    columns = [col.name for col in table.columns]
    has_run_id = "run_id" in columns

    return {
        "schema": metadata.schema or schema_name.lower(),
        "table": table_name,
        "columns": columns,
        "has_run_id": has_run_id,
    }


def get_schemas_and_tables() -> Dict[str, List[str]]:
    """
    Get a dictionary mapping schema names to their table lists.

    Returns:
        Dict[str, List[str]]: Dictionary with schema names as keys and
            lists of table names as values
    """
    result = {}
    for schema_name in get_available_schemas():
        try:
            result[schema_name] = get_schema_tables(schema_name)
        except Exception:
            # Skip schemas that can't be introspected
            continue
    return result
