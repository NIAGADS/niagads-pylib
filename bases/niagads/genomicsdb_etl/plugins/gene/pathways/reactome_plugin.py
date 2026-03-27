from niagads.etl.plugins.base import AbstractBasePlugin, LoadStrategy
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
    ResumeCheckpoint,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.genomicsdb.schema.admin.pipeline import ETLOperation
from niagads.csv_parser.core import CSVFileParser
from niagads.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.genomicsdb.schema.gene.gene_models import Gene, GeneIdentifierType
from niagads.genomicsdb.schema.reference.pathway import Pathway
from niagads.genomicsdb_service.etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from pydantic import BaseModel, Field, field_validator
from typing import List
from sqlalchemy.exc import (
    MultipleResultsFound,
    NoResultFound,
)  # TODO: EGA - make wrappers
from .helpers import load_pathway
from .types import PathwayAnnotation

# Define column names for Reactome file
COLUMN_NAMES = [
    "gene_id",
    "pathway_id",
    "pathway_url",
    "pathway_name",
    "evidence_code",
    "species",
]


# class GenePathwayAnnotation(BaseModel):
# id: str = Field(alias="gene_id")
# pathway_id: str
# pathway_name: str
# evidence_code: str

# model_config = {"extra": "ignore"}


class ReactomeLoaderParams(
    BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin
):
    """Parameter model for ReactomeLoader plugin."""

    file: str = Field(..., description="Reactome CSV file to load")

    # Validate that the file exists
    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)

    @field_validator("file", mode="before")
    def validate_format(cls, file_name: str) -> str:
        """
        Validates that the CSV file has the expected number of columns.

        Reactome files have no header row, validate by checking
        the column count of the first data row. This will help
        us to notice if the data gets updated.

        Args:
            file_name: Path to Reactome file

        Returns:
            str: The validated file

        Raises:
            ValueError: If the file format is invalid or has been updated
        """
        # Only read first line to check column count
        with open(file_name, "r", encoding="utf-8", errors="ignore") as fh:
            first_line = fh.readline().strip()
            values = first_line.split("\t")

        # Check column count
        if len(COLUMN_NAMES) != len(values):
            raise ValueError(
                f"Expected {len(COLUMN_NAMES)} columns, found {len(values)} columns.\n"
            )

        # Check that column 3 (pathway_url) starts with 'https:'
        if not values[2].startswith("https:"):
            raise ValueError(
                f"Column 3 (pathway_url) should start with 'https:', found: '{values[2]}'\n"
            )

        return file_name


@PluginRegistry.register(metadata={"version": 1.0})
class ReactomeLoaderPlugin(AbstractBasePlugin):
    """
    Plugin for loading Reactome data.

    This plugin extracts, transforms, and loads Reactome pathway annotations
    for integration into the genome browser.
    """

    _params: ReactomeLoaderParams

    @classmethod
    def description(cls):
        return "Loads and processes Reactome pathway data from CSV files."

    @classmethod
    def parameter_model(cls):
        return ReactomeLoaderParams

    @property
    def operation(self):
        return ETLOperation.INSERT

    @property
    def affected_tables(self):
        # TODO: Replace with actual table name(s)
        return [Pathway.table_name(), PathwayMembership.table_name()]

    @property
    def load_strategy(self):
        return LoadStrategy.BULK

    def extract(self):
        """
        Extract Reactome data from file.

        Reads the file into a DataFrame (without header) and filters for:
        - Species: Homo sapiens
        - Gene IDs starting with "ENSG" (Ensembl gene IDs)

        Yields:
            DataFrame: Filtered Reactome data with assigned column names
        """
        # Debug mode
        self.logger.debug(f"Parsing Reactome file: {self._params.file}")

        # Parse CSV file
        parser = CSVFileParser(self._params.file)
        parser.strip(True)  # Strip whitespace

        # Read into DataFrame with no header and assign column names
        df = parser.to_pandas_df(header=None, names=COLUMN_NAMES)

        # Log file dimensions
        self.logger.info(
            f"File loaded with {len(df)} rows and {len(df.columns)} columns"
        )

        # Debug logger in case columns aren't loaded properly with column headers
        self.logger.debug(
            f"Successfully parsed {len(df.columns)} columns from file. Columns: {list(df.columns)}"
        )

        # Filter for Homo sapiens
        filtered_df = df[df["species"] == "Homo sapiens"]
        self.logger.debug(
            f"Filtered by species 'Homo sapiens', remaining rows: {len(filtered_df)}"
        )

        # Filter for Ensembl gene IDs (starting with "ENSG")
        filtered_df = filtered_df[
            filtered_df["gene_id"].str.startswith("ENSG", na=False)
        ]
        self.logger.debug(
            f"Filtered by gene ID prefix 'ENSG', remaining rows: {len(filtered_df)}"
        )

        # Log completion
        self.logger.info(
            f"Data extraction complete with {len(filtered_df)} filtered rows"
        )

        return filtered_df.to_dict(orient="dict")

    def transform(self, data: list):
        """
        Transform the extracted DataFrame into a list of PathwayAnnotation objects.

        Args:
            data: Filtered DataFrame from extract step

        Returns:
            List[PathwayAnnotation]: List of transformed records for loading
        """
        self.logger.debug(f"Starting transformation with {len(data)} input rows")

        # Transform DataFrame to list of PathwayAnnotation objects
        records = [PathwayAnnotation(**row) for row in data]

        self.logger.info(f"Transformation complete with {len(records)} records")

        return records

    async def load(
        self, transformed: List[PathwayAnnotation], session
    ) -> ResumeCheckpoint:
        """
        Load transformed records into the database.

        Args:
            transformed: List of transformed pathway annotations.
            session: Database session.

        Returns:
            ResumeCheckpoint: The checkpoint for resuming the ETL process.
        """
        return await load_pathway(
            self, session, transformed, GeneIdentifierType.ENSEMBL
        )

    def get_record_id(self, record: dict) -> str:
        """
        Get unique identifier for a record.

        Uses combination of gene_id and pathway_id as unique identifier.

        Args:
            record: Record dict

        Returns:
            str: Unique identifier
        """
        return f"{record['pathway_id']}:{record['gene_id']}"
