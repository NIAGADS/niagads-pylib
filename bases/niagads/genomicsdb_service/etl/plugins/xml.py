"""
Sample ETL plugin for loading XML data into a database table using the NIAGADS ETL framework.

- Expects an XML file with repeated blocks, each block corresponding to a row.
- The outermost XML tag (e.g., <NIAGADS::AlleleFreqPopulation>) determines the schema.table to load into.

"""

import xml.etree.ElementTree as ET
import re
from typing import Any, Dict, Iterator, List, Optional, Type
from niagads.etl.plugins.base import AbstractBasePlugin, ETLMode
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from pydantic import Field, ConfigDict, BaseModel
from sqlalchemy import text


class XMLRecord(BaseModel):
    table: str
    schema: str

    model_config = ConfigDict(extra='allow')
    
    # TODO: add column getter from extras
    


class XMLRecordLoaderParams(BasePluginParams, PathValidatorMixin):
    file: str = Field(description="full path to the XML file")
    update: Optional[bool] = Field(
        default=False,
        description="plugin will updating existing records; otherwise will throw and error",
    )

    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)


@PluginRegistry.register(metadata={"version": 1.0})
class XMLRecordLoader(AbstractBasePlugin):
    _params: XMLRecordLoaderParams  # type annotation

    @classmethod
    def parameter_model(cls) -> Type[BasePluginParams]:
        return XMLRecordLoaderParams

    @classmethod
    def description(self):
        description = """
        XML Loader modeled after the VEuPathDB LoadGusXml Plugin
        see: https://github.com/VEuPathDB/GusAppFramework/blob/cf9a99dba00bea3875f9eb5128294ed4a7a25377/Supported/plugin/perl/LoadGusXml.pm
        
        Inserts or updates data into any table using a simple XML format.  
        The format is as follows:
        
        The XML format is:
            <Record schema="schema" table="table">
                <column>value</column>
                ...
            </Record>
            ...
            Each major tag represents a row in a table and nested within it are elements for 
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
        """
        Parse the XML file and return all unique schema.table combinations from <Table> tags.
        This is robust and independent of extract().
        """
        tables = set()
        try:
            tree = ET.parse(self._params.file)
            root = tree.getroot()
            for table_elem in root.findall("Table"):
                schema = table_elem.attrib.get("schema", "").lower()
                table = table_elem.attrib.get("name", "").lower()
                if schema and table:
                    tables.add(f"{schema}.{table}")
        except Exception as e:
            self.logger.warning(f"XMLRecordLoader.affected_tables: Could not parse tables - {e}")
        return sorted(tables)

    @property
    def streaming(self) -> bool:
        return True

    def extract(self) -> Iterator[XMLRecord]:
        if self._debug:
            self.logger.debug(
                f"XMLRecordLoader.extract: Parsing file {self._params.file}"
            )
    
        try:
            tree = ET.parse(self._params.file)
            root = tree.getroot()
            
            for table_elem in root.findall("Table"):
                schema = table_elem.attrib.get("schema", "").lower()
                table = table_elem.attrib.get("name", "").lower()
                
                if not schema or not table:
                    raise ValueError("Missing 'schema' or 'name' attribute in <Table> tag.")
                
                for record_elem in table_elem.findall("Record"):
                    data = {child.tag: child.text for child in record_elem}
                    record = XMLRecord(schema=schema, table=table, **data)
                    if self._debug:
                        self.logger.debug(f"XMLRecordLoader.extract: Yielding row {record.model_dump()}")
                    yield record
                    
        except Exception as e:
            self.logger.error(f"XMLRecordLoader.extract: Error - {e}")
            raise

    def transform(self, data: XMLRecord) -> XMLRecord:
        if self._debug:
            self.logger.debug(f"XMLRecordLoader.transform: Transforming data {data}")
        if data is None:
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )
        return data

    def _construct_filter_clause(self, columns: List[str]) -> str:
        return " AND ".join([f"{col} = :{col}" for col in columns])

    async def _record_exists(
        self, session, record: XMLRecord, columns: List[str]
    ) -> bool:
        where_clause = self._construct_filter_clause(columns)
        select_sql = (
            f"SELECT 1 FROM {record.schema}.{record.table} WHERE {where_clause} LIMIT 1"
        )
        params = {col: getattr(record, col) for col in columns}
        result = await session.execute(text(select_sql), params)
        return result.scalar() is not None

    async def _insert_record(self, session, record: XMLRecord, columns: List[str]):
        col_names = ", ".join(columns)
        placeholders = ", ".join(f":{col}" for col in columns)
        sql = f"INSERT INTO {record.schema}.{record.table} ({col_names}) VALUES ({placeholders})"
        params = {col: getattr(record, col) for col in columns}
        await session.execute(text(sql), params)

    async def _update_record(self, session, record: XMLRecord, columns: List[str]):
        set_clause = ", ".join([f"{col} = :{col}" for col in columns])
        where_clause = self._construct_filter_clause(columns)
        update_sql = (
            f"UPDATE {record.schema}.{record.table} SET {set_clause} WHERE {where_clause}"
        )
        params = {col: getattr(record, col) for col in columns}
        await session.execute(text(update_sql), params)

    async def load(self, transformed: List[XMLRecord], mode: ETLMode) -> int:
        """
        Insert or update records in the target table based on XML input.
        For each row:
        - Checks if the record already exists in the table (using all columns as a composite key).
        - If not, inserts the record.
        - If it exists and --update is True, updates the record.
        - If it exists and --update is False, raises an error.
        Args:
            transformed (List[XMLRecord]): List of parsed and transformed XMLRecord objects.
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).
        Returns:
            int: Number of records inserted (not updated).
        """
        if self._debug:
            self.logger.debug(
                f"XMLRecordLoader.load: Loading {len(transformed)} records"
            )
        if not transformed or len(transformed) == 0:
            raise RuntimeError(
                "No records provided to load(). At least one record is required."
            )

        inserted = 0
        table_counts = {}

        async with self._session_manager() as session:
            for record in transformed:
                table_key = f"{record.schema}.{record.table}"
                if table_key not in table_counts:
                    table_counts[table_key] = 0

                columns = [k for k in record.model_fields.keys() if k not in ("schema", "table")]

                if self._debug:
                    self.logger.debug(f"XMLRecordLoader.load: Processing record {record} for {table_key}")

                exists = await self._record_exists(session, record, columns)

                if not exists:
                    await self._insert_record(session, record, columns)
                    inserted += 1
                    table_counts[table_key] += 1
                    if self._debug:
                        self.logger.debug(f"XMLRecordLoader.load: Inserted record {record}")
                else:
                    if self._params.update:
                        await self._update_record(session, record, columns)
                        if self._debug:
                            self.logger.debug(
                                f"XMLRecordLoader.load: Updated record {record}"
                            )
                    else:
                        if self._debug:
                            self.logger.warning(
                                f"XMLRecordLoader.load: Record exists and update not enabled: {record}"
                            )
                        raise RuntimeError(
                            f"Record already exists and update is not enabled: {record}"
                        )

            if mode == ETLMode.COMMIT:
                await session.commit()
                if self._debug:
                    self.logger.debug(f"XMLRecordLoader.load: Committed transaction.")
            elif mode == ETLMode.NON_COMMIT:
                await session.rollback()
                if self._debug:
                    self.logger.debug(f"XMLRecordLoader.load: Rolled back transaction.")

        # Log the number of records loaded per table
        for table_key, count in table_counts.items():
            self.logger.info(f"XMLRecordLoader.load: Loaded {count} records into {table_key}")

        return inserted

    def get_record_id(self, record: Dict[str, Any]) -> Optional[str]:
        # no way to know
        return None
