"""
Sample ETL plugin for loading XML data into a database table using the NIAGADS ETL framework.

- Expects an XML file with repeated blocks, each block corresponding to a row.
- The outermost XML tag (e.g., <NIAGADS::AlleleFreqPopulation>) determines the schema.table to load into.

"""

import xml.etree.ElementTree as ET
import re
from typing import Any, Dict, Iterator, List, Optional, Type
from niagads.pipeline.plugins.base import AbstractBasePlugin, BasePluginParams, ETLMode
from niagads.pipeline.plugins.registry import PluginRegistry
from pydantic import Field
from sqlalchemy import text


class XMLLoaderParams(BasePluginParams):
    file: str = Field(description="full path to the XML file")
    update: Optional[bool] = Field(
        default=False,
        description="plugin will updating existing records; otherwise will throw and error",
    )


@PluginRegistry.register(metadata={"version": 1.0})
class XMLLoaderPlugin(AbstractBasePlugin):
    _params: XMLLoaderParams  # type annotation

    @classmethod
    def parameter_model(cls) -> Type[BasePluginParams]:
        return XMLLoaderParams

    @property
    def description(self):
        description = """
        XML Loader modeled after the VEuPathDB LoadGusXml Plugin
        see: https://github.com/VEuPathDB/GusAppFramework/blob/cf9a99dba00bea3875f9eb5128294ed4a7a25377/Supported/plugin/perl/LoadGusXml.pm
        
        Inserts or updates data into any table using a simple XML format.  
        The format is as follows:
        
        The XML format is:
            <Schema::Table>
                <column>value</column>
                ...
            </Schema::Table>
            ...
            Each major tag represents a table and nested within it are elements for 
            column values. 
            
            If the row already exists in the table, the plugin will throw an error unless
            the --update flag is specified.
        """
        return description

    @property
    def operation(self):
        # Use the appropriate ETLOperation for your use case
        from niagads.genomicsdb.models.admin.pipeline import ETLOperation

        return ETLOperation.INSERT

    @property
    def affected_tables(self) -> List[str]:
        # Return the inferred table if available, else empty list
        if hasattr(self, "_schema") and hasattr(self, "_table"):
            return [f"{self._schema}.{self._table}"]
        return []

    @property
    def streaming(self) -> bool:
        return True

    def _parse_schema_table(self, tag: str):
        """
        Parse schema and table from tag like 'NIAGADS::AlleleFreqPopulation'.
        Returns (schema, table) as lowercase, underscores.
        """
        m = re.match(r"([A-Za-z0-9_]+)::([A-Za-z0-9_]+)", tag)
        if not m:
            raise ValueError(f"Cannot parse schema and table from tag: {tag}")
        schema = m.group(1).lower()
        # Convert CamelCase to snake_case
        table = re.sub(r"(?<!^)(?=[A-Z])", "_", m.group(2)).lower()
        return schema, table

    def extract(self) -> Iterator[Dict[str, Any]]:
        tree = ET.parse(self._params.file)
        root = tree.getroot()
        self._schema, self._table = self._parse_schema_table(root.tag)
        for elem in root.iter(root.tag):
            row = {child.tag: child.text for child in elem}
            yield row

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Optionally clean/convert data here
        if data is None or len(data) == 0:
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )
        return data

    def _construct_filter_clause(self, columns: List[str]) -> str:
        return " AND ".join([f"{col} = :{col}" for col in columns])

    async def _record_exists(
        self, session, row: Dict[str, Any], columns: List[str]
    ) -> bool:
        where_clause = self._construct_filter_clause(columns)
        select_sql = (
            f"SELECT 1 FROM {self._schema}.{self._table} WHERE {where_clause} LIMIT 1"
        )
        result = await session.execute(text(select_sql), row)
        return result.scalar() is not None

    async def _insert_record(self, session, row: Dict[str, Any], columns: List[str]):
        col_names = ", ".join(columns)
        placeholders = ", ".join(f":{col}" for col in columns)
        sql = f"INSERT INTO {self._schema}.{self._table} ({col_names}) VALUES ({placeholders})"
        await session.execute(text(sql), row)

    async def _update_record(self, session, row: Dict[str, Any], columns: List[str]):
        set_clause = ", ".join([f"{col} = :{col}" for col in columns])
        where_clause = self._construct_filter_clause(columns)
        update_sql = (
            f"UPDATE {self._schema}.{self._table} SET {set_clause} WHERE {where_clause}"
        )
        await session.execute(text(update_sql), row)

    async def load(self, transformed: List[Dict[str, Any]], mode: ETLMode) -> int:
        """
        Insert or update records in the target table based on XML input.

        For each row:
        - Checks if the record already exists in the table (using all columns as a composite key).
        - If not, inserts the record.
        - If it exists and --update is True, updates the record.
        - If it exists and --update is False, raises an error.

        Args:
            transformed (List[Dict[str, Any]]): List of parsed and transformed records.
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).

        Returns:
            int: Number of records inserted (not updated).
        """

        if not transformed or len(transformed) == 0:
            raise RuntimeError(
                "No records provided to load(). At least one record is required."
            )

        if not hasattr(self, "_schema") or not hasattr(self, "_table"):
            raise RuntimeError("Schema/table not set. Did you call extract()?")

        async with self._session_manager() as session:
            columns = list(transformed[0].keys())
            inserted = 0
            for row in transformed:
                exists = await self._record_exists(session, row, columns)
                if not exists:
                    await self._insert_record(session, row, columns)
                    inserted += 1
                else:
                    if self._params.update:
                        await self._update_record(session, row, columns)
                    else:
                        raise RuntimeError(
                            f"Row already exists and update is not enabled: {row}"
                        )
            if mode == ETLMode.COMMIT:
                await session.commit()
            elif mode == ETLMode.NON_COMMIT:
                await session.rollback()
            return inserted

    def get_record_id(self, record: Dict[str, Any]) -> Optional[str]:
        # no way to know
        return None
