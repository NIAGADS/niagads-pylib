"""
Sample ETL plugin for loading XML data into a database table using the NIAGADS ETL framework.

- Expects an XML file with repeated blocks, each block corresponding to a row.
- The outermost XML tag (e.g., <NIAGADS::AlleleFreqPopulation>) determines the schema.table to load into.
- Assumes a SQLAlchemy model exists for the table.
"""

import xml.etree.ElementTree as ET
import re
from typing import Any, Dict, Iterator, List, Optional, Type
from niagads.pipeline.plugins.base import AbstractBasePlugin, BasePluginParams, ETLMode
from sqlalchemy import text


class XMLLoaderParams(BasePluginParams):
    xml_file: str


class XMLLoaderPlugin(AbstractBasePlugin):
    @classmethod
    def parameter_model(cls) -> Type[BasePluginParams]:
        return XMLLoaderParams

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
        tree = ET.parse(self._params.xml_file)
        root = tree.getroot()
        self._schema, self._table = self._parse_schema_table(root.tag)
        for elem in root.iter(root.tag):
            row = {child.tag: child.text for child in elem}
            yield row

    def transform(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Optionally clean/convert data here
        return data

    async def load(self, transformed: List[Dict[str, Any]], mode: ETLMode) -> int:
        if not hasattr(self, "_schema") or not hasattr(self, "_table"):
            raise RuntimeError("Schema/table not set. Did you call extract()?")
        async with self._session_manager() as session:
            if not transformed:
                return 0
            columns = list(transformed[0].keys())
            col_names = ", ".join(columns)
            placeholders = ", ".join(f":{col}" for col in columns)
            sql = f"INSERT INTO {self._schema}.{self._table} ({col_names}) VALUES ({placeholders})"
            for row in transformed:
                await session.execute(text(sql), row)
            if mode == ETLMode.COMMIT:
                await session.commit()
            elif mode == ETLMode.NON_COMMIT:
                await session.rollback()
            return len(transformed)

    def get_record_id(self, record: Dict[str, Any]) -> Optional[str]:
        # no way to know
        return None
