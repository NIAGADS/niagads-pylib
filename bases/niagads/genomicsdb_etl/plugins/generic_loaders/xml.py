"""
ETL plugin for loading or updating a record in an arbitrary table.
"""

import ast
import importlib.resources

from typing import Any, Dict, Iterator, List, Optional, Type

from lxml import etree
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.admin.types import TableRef
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
    ResumeCheckpoint,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.utils.string import dict_to_info_string, is_number, to_number
from pydantic import BaseModel, ConfigDict, Field


class XMLEntry(BaseModel):
    data_table: str
    data_schema: str

    model_config = ConfigDict(extra="allow")

    @property
    def qualified_table_name(self):
        return f"{self.data_schema}.{self.data_table}"

    def __str__(self):
        return str(self.model_dump(include_table_schema=True))

    def has_field(self, field: str) -> bool:
        """
        Returns True if a table field (field) is present in this record.
        """
        return field in self.model_dump()

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


class XMLRecordLoaderParams(BasePluginParams, PathValidatorMixin):
    file: str = Field(description="Full path to the XML file to load.")

    skip_duplicates: Optional[bool] = Field(
        default=False,
        description="If True, will log and skip records already existing in the database; If false will raise error",
    )

    validate_file_exists = PathValidatorMixin.validator("file")


metadata = PluginMetadata(
    version="1.0",
    description="""
        XML Record Loader 
        
        Used to load or update small datasets or single records into any existing 
        table without having to write a task-specific plugin. 
        
        Inserts or updates data into/in any table using a simple XML format.  
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
        the --skip-duplicates flag is specified.
        """,
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.LOAD,
    is_large_dataset=False,
    parameter_model=XMLRecordLoaderParams,
)


@PluginRegistry.register(metadata)
class XMLRecordLoader(AbstractBasePlugin):
    _params: XMLRecordLoaderParams  # type annotation

    def __init__(
        self,
        params,
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self.__table_ref_lookup: dict = {}

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
                "niagads.genomicsdb_etl.plugins.validation_schemas",
                "records.xsd",
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

    def extract(self) -> Iterator[XMLEntry]:
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

                        # identify numbers
                        if is_number(value):
                            value = to_number(value)

                        # convert nested dicts and arrays to correct python types
                        if isinstance(value, str) and (
                            value.startswith("[") or value.startswith("{}")
                        ):
                            value = ast.literal_eval(value)
                        data[col_name] = value

                    record = XMLEntry(data_schema=schema, data_table=table, **data)
                    self.logger.debug(
                        f"Yielding row {record.model_dump(include_table_schema=True)}"
                    )
                    yield record

        except Exception as e:
            self.logger.error(f"Error - {e}")
            raise

    async def transform(self, data: XMLEntry) -> XMLEntry:
        return data

    async def __lookup_table_ref(self, session, qualified_table_name: str):
        """
        Retrieve and cache a TableRef for the given qualified table name.

        Looks up the TableRef in the local cache; if not present, fetches it from the TableCatalog
        and stores it in the cache for future use.
        """
        table_ref: TableRef = self.__table_ref_lookup.get(qualified_table_name, None)
        if table_ref is None:
            table_ref = await TableCatalog.get_table_ref(session, qualified_table_name)
            self.__table_ref_lookup[qualified_table_name] = table_ref
        return table_ref

    async def __existing_record(self, session, entry: XMLEntry) -> bool:
        """
        Checks if an existing record (by primary key or stable identifier) exists
        in the database for the given entry, if so fetches it

        If the primary key field is present in the entry, verifies the record exists by primary key.
        If not, but a stable identifier field is present, verifies by stable identifier.
        Raises ValueError if the record does not exist for update.

        Returns None if no record found or neither field is present
        """

        table_ref = await self.__lookup_table_ref(session, entry.qualified_table_name)
        table_class = table_ref.table_class
        table_pk_field = table_ref.table_primary_key
        table_stable_id_field = table_ref.table_stable_id

        existing_record = None
        if entry.has_field(table_pk_field):
            # check primary key first because if both primary key and stable_id are provided
            # the user likely wants to update the stable_id
            primary_key = getattr(entry, table_pk_field)
            self.logger.debug(
                f"Looking up record by primary_key: {entry.qualified_table_name} - {primary_key}"
            )
            try:
                existing_record = await table_class.fetch_record(
                    session, filters={table_pk_field: primary_key}
                )
            except:
                raise ValueError(
                    "Attempting to update record with invalid primary key: "
                    f"{entry.model_dump(include_table_schema=True)}"
                )
        elif entry.has_field(table_stable_id_field):
            stable_id = getattr(entry, table_stable_id_field)
            self.logger.debug(
                f"Looking up record by stable_id: {entry.qualified_table_name} - {stable_id}"
            )
            try:
                existing_record = await table_class.fetch_record(
                    session, filters={table_stable_id_field: stable_id}
                )
            except:
                raise ValueError(
                    "Attempting to update record with invalid stable identifier: "
                    f"{entry.model_dump(include_table_schema=True)}"
                )
        return existing_record

    async def __is_duplicate(self, session, entry: XMLEntry):
        """
        Checks if the given entry would be a duplicate in the database.

        Looks up the table reference and ORM class, instantiates a record from the entry,
        and checks for existence in the database using the ORM's exists method.
        """
        table_ref = await self.__lookup_table_ref(session, entry.qualified_table_name)
        table_class = table_ref.table_class
        record = table_class(**entry.model_dump())
        return await record.exists(session)

    async def __insert_record(self, session, entry: XMLEntry):
        table_ref = await self.__lookup_table_ref(session, entry.qualified_table_name)
        table_class = table_ref.table_class
        record = table_class(**entry.model_dump())
        await record.submit(session)

    async def __update_record(self, session, entry: XMLEntry, record):
        """
        Update the fields of the record with values from entry, then call update.
        """
        for field, value in entry.model_dump().items():
            setattr(record, field, value)
        await record.update(session)

    async def load(self, session, entries: List[XMLEntry]) -> ResumeCheckpoint:
        """
        Load XML records into the target table, performing insert or update as needed.

        For each entry:
          - If a matching record exists (by primary key or stable identifier), update it.
          - If not, check for duplicates; if found and skip_duplicates is True, skip; else, raise error.
          - Otherwise, insert the new record
        """

        for entry in entries:
            self.logger.debug(f"Processing record {entry}")

            existing_record = await self.__existing_record(session, entry)

            if existing_record is not None:
                await self.__update_record(session, entry, existing_record)
            else:
                is_duplicate: bool = await self.__is_duplicate(session, entry)
                if is_duplicate:
                    if self._params.skip_duplicates:
                        self.logger.info(
                            f"Skipped existing record in {entry.qualified_table_name}: {entry}"
                        )
                        self.inc_tx_count(entry.qualified_table_name, ETLOperation.SKIP)
                    else:
                        raise ValueError(
                            f"Cannot insert duplicate record: {entry.model_dump(include_table_schema=True)}"
                        )
                else:
                    await self.__insert_record(session, entry)

        return self.create_checkpoint(record=entries[-1])

    def get_record_id(self, entry: XMLEntry) -> Optional[str]:
        return dict_to_info_string(entry.model_dump(include_table_schema=True))
