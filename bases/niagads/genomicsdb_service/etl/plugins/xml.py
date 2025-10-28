"""
Sample ETL plugin for loading XML data into a database table using the NIAGADS ETL framework.

- Expects an XML file with repeated blocks, each block corresponding to a row.
- The outermost XML tag (e.g., <NIAGADS::AlleleFreqPopulation>) determines the schema.table to load into.

"""

from lxml import etree
from typing import Any, Dict, Iterator, List, Optional, Type
from niagads.etl.plugins.base import AbstractBasePlugin, ETLMode
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from pydantic import Field, ConfigDict, BaseModel, computed_field
from sqlalchemy import text
import importlib.resources


class SQLClauses(BaseModel):
    columns: List[str]
    col_names: str
    placeholders: str
    set_clause: str
    where_clause: str


class XMLRecord(BaseModel):
    data_table: str
    data_schema: str

    model_config = ConfigDict(extra="allow")

    def __str__(self):
        return str(self.model_dump(include_table_schema=True))

    def model_dump(
        self, *args, include_table_schema: bool = False, **kwargs
    ) -> Dict[str, Any]:
        """
        Override model_dump to return only the extra fields (not schema/table/sql_clauses) for this XMLRecord.
        Uses __pydantic_extra__ for Pydantic v2.
        If include_table_schema is True, include data_schema and data_table in the output.
        """
        result = (
            dict(self.__pydantic_extra__)
            if hasattr(self, "__pydantic_extra__") and self.__pydantic_extra__
            else None
        )
        if result is not None:
            if include_table_schema:
                result["schema"] = self.data_schema
                result["table"] = self.data_table
            return result
        raise RuntimeError(
            "XMLRecord: No extra fields found. This likely indicates an issue parsing the XML record."
        )

    @computed_field
    @property
    def sql_clauses(self) -> SQLClauses:
        """
        Computed property to extract SQL clauses from a record as a Pydantic model.
        """

        columns = list(self.model_dump().keys())
        return SQLClauses(
            columns=columns,
            col_names=", ".join(columns),
            placeholders=", ".join(f":{col}" for col in columns),
            set_clause=", ".join([f"{col} = :{col}" for col in columns]),
            where_clause=" AND ".join([f"{col} = :{col}" for col in columns]),
        )


class XMLRecordLoaderParams(BasePluginParams, PathValidatorMixin):
    file: str = Field(description="Full path to the XML file to load.")
    update: Optional[bool] = Field(
        default=False,
        description="If True, plugin will update existing records; otherwise will handle duplicates according to value of `--skip-existing` option",
    )
    skip_existing: Optional[bool] = Field(
        default=False,
        description="If True, will log and skip records already existing in the database, otherwise the plugin will throw an error when duplicate records are detected (ignored if `--update` is True).",
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
        XML Record Loader 
        
        Used to load or update small datasets or single records into any existing 
        table without having to write a task-specific plugin. 
        
        TODO: Can be used in conjuction with planned CSV -> XML converter
        
        Inserts or updates data into any table using a simple XML format.  
        The format is as follows:
        
        The XML format is:
            <Records>
                <Table schema="schema" name="table">
                    <Record>
                        <Field name="column">value</Field>
                        ...
                    </Record>
                    ...
                </Table>
                ...
            </Records>
            
        Each <Table> tag represents a table, and each <Record> tag within it is a row. 
        Nested elements within <Record> are columns and their values.
        
        If the row already exists in the table, the plugin will throw an error unless
        the --update flag is specified.
        """
        return description

    @property
    def operation(self):
        # Use the appropriate ETLOperation for your use case
        from niagads.genomicsdb.models.admin.pipeline import ETLOperation

        return ETLOperation.INSERT

    def _parse_and_validate_xml(self) -> "etree._Element":
        """
        Helper to load and validate XML file against XSD, returning the root element.
        Uses package-relative path for XSD.
        """
        try:
            with open(self._params.file, "rb") as xml_file:
                xml_content = xml_file.read()
            # Use importlib.resources to load records.xsd from the package
            with importlib.resources.open_binary(
                "niagads.genomicsdb_service.etl.plugins.validators", "records.xsd"
            ) as xsd_file:
                schema_root = etree.XML(xsd_file.read())
            schema = etree.XMLSchema(schema_root)
            parser = etree.XMLParser(schema=schema)
            return etree.fromstring(xml_content, parser)
        except etree.XMLSyntaxError as e:
            msg = (
                f"XML syntax error: {e.msg} (line {e.lineno}, column {e.position[1]})\n"
                f"Check that your XML file is well-formed and starts with the <Records> root element."
            )
            self.logger.exception(f"XMLRecordLoader._parse_and_validate_xml: {msg}")
            raise RuntimeError(msg)
        except etree.DocumentInvalid as e:
            msg = (
                f"XML validation error: {e.error_log.last_error}\n"
                f"Ensure your XML matches the expected schema. The root element should be <Records> containing <Table> and <Record> elements."
            )
            self.logger.exception(f"XMLRecordLoader._parse_and_validate_xml: {msg}")
            raise RuntimeError(msg)
        except Exception as e:
            msg = f"Unexpected error parsing XML: {str(e)}"
            self.logger.exception(f"XMLRecordLoader._parse_and_validate_xml: {msg}")
            raise RuntimeError(msg)

    @property
    def affected_tables(self) -> List[str]:
        """
        Parse the XML file and return all unique schema.table combinations from <Table> tags.
        This is robust and independent of extract().
        """
        tables = set()
        try:
            root = self._parse_and_validate_xml()
            for table_elem in root.findall("Table"):
                schema_attr = table_elem.attrib.get("schema", "").lower()
                table_attr = table_elem.attrib.get("name", "").lower()
                if schema_attr and table_attr:
                    tables.add(f"{schema_attr}.{table_attr}")
        except Exception as e:
            self.logger.warning(
                f"XMLRecordLoader.affected_tables: Could not parse tables - {e}"
            )
        return sorted(tables)

    @property
    def streaming(self) -> bool:
        return True

    def extract(self) -> Iterator[XMLRecord]:
        if self._debug:
            self.logger.debug(f"Parsing file {self._params.file}")

        try:
            root = self._parse_and_validate_xml()
            for table_elem in root.findall("Table"):
                schema = table_elem.attrib.get("schema", "").lower()
                table = table_elem.attrib.get("name", "").lower()

                if not schema or not table:
                    raise ValueError(
                        "Missing 'schema' or 'name' attribute in <Table> tag."
                    )

                for record_elem in table_elem.findall("Record"):
                    data: Dict[str, Any] = {}
                    for child in record_elem:
                        # Use the 'name' attribute as the column name when present; fall back to the element tag
                        col_name = child.attrib.get("name") or child.tag
                        if col_name in data:
                            # duplicate column names in a single record are ambiguous
                            raise ValueError(
                                f"Duplicate field name '{col_name}' in record for table {schema}.{table}"
                            )
                        # normalize whitespace; preserve empty/null semantics
                        value = child.text.strip() if child.text is not None else None
                        data[col_name] = value

                    record = XMLRecord(data_schema=schema, data_table=table, **data)
                    if self._debug:
                        self.logger.debug(
                            f"Yielding row {record.model_dump(include_table_schema=True)}"
                        )
                    yield record

        except Exception as e:
            self.logger.error(f"Error - {e}")
            raise

    def transform(self, data: XMLRecord) -> XMLRecord:
        if self._debug:
            self.logger.debug("Transforming data", data)
        if data is None:
            raise RuntimeError(
                "No records provided to transform(). At least one record is required."
            )
        return data

    async def _record_exists(self, session, record: XMLRecord) -> bool:
        select_sql = f"SELECT 1 FROM {record.data_schema}.{record.data_table} WHERE {record.sql_clauses.where_clause} LIMIT 1"
        result = await session.execute(text(select_sql), record.model_dump())
        return result.scalar() is not None

    async def _insert_record(self, session, record: XMLRecord):
        sql = f"INSERT INTO {record.data_schema}.{record.data_table} ({record.sql_clauses.col_names}) VALUES ({record.sql_clauses.placeholders})"
        await session.execute(text(sql), record.model_dump())

    async def _update_record(self, session, record: XMLRecord):
        update_sql = f"UPDATE {record.data_schema}.{record.data_table} SET {record.sql_clauses.set_clause} WHERE {record.sql_clauses.where_clause}"
        await session.execute(text(update_sql), record.model_dump())

    async def load(self, transformed: List[XMLRecord], mode: ETLMode) -> int:
        """
        Insert or update records in the target table based on XML input.
        For each row:
        - Checks if the record already exists in the table (using all columns as a composite key).
        - If not, inserts the record.
        - If it exists and --update is True, updates the record.
        - If it exists and --skip-existing is True, logs and skips the record.
        - If it exists and neither --update nor --skip-existing is True, raises an error.
        Args:
            transformed (List[XMLRecord]): List of parsed and transformed XMLRecord objects.
            mode (ETLMode): ETL execution mode (COMMIT, NON_COMMIT, DRY_RUN).
        Returns:
            int: Number of records inserted (not updated).
        """
        if self._debug:
            self.logger.debug(f"Loading {len(transformed)} records")
        if not transformed or len(transformed) == 0:
            raise RuntimeError(
                "No records provided to load(). At least one record is required."
            )

        transaction_count = 0
        async with self._session_manager() as session:
            for record in transformed:
                table_key = f"{record.data_schema}.{record.data_table}"

                if self._debug:
                    self.logger.debug(f"Processing record {record} for {table_key}")

                exists = await self._record_exists(session, record)

                if not exists:
                    await self._insert_record(session, record)
                    self.update_transaction_count("inserts", table_key)
                    transaction_count += 1
                    if self._debug:
                        self.logger.debug(f"Inserted record {record}")

                else:
                    if self._params.update:
                        await self._update_record(session, record)
                        self.update_transaction_count("updates", table_key)
                        transaction_count += 1
                        if self._debug:
                            self.logger.debug(f"Updated record {record}")

                    elif self._params.skip_existing:
                        self.logger.info(
                            f"Skipped existing record in {table_key}: {record}"
                        )
                        self.update_transaction_count("skips", table_key)
                        continue

                    else:
                        if self._debug:
                            self.logger.warning(
                                f"Record exists and update/skip_existing not enabled: {record}"
                            )
                        raise RuntimeError(
                            f"Record already exists and update/skip_existing is not enabled: {record}"
                        )

            if mode == ETLMode.COMMIT:
                await session.commit()
                if self._debug:
                    self.logger.debug(f"Committed transaction.")

            elif mode == ETLMode.NON_COMMIT:
                await session.rollback()
                if self._debug:
                    self.logger.debug(f"Rolled back transaction.")

        return transaction_count

    def get_record_id(self, record: Dict[str, Any]) -> Optional[str]:
        # no way to know
        return None
