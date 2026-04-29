"""
TODOs:

* remove bad (not unused, but bad) imports
* build the PluginMetadata Object, delete the obsolete @properties that define the same info
* clean up the logging statements, review them and make sure info, vs debug, vs "verbose"
   * add a temporary critical logging statement in extract to make sure dataframe header is as expected
* update transform to transform ReactomeEntries into GenePathwayAssociations
  * figure out how to aggregate the member gene list
* remove unused imports
* review w/EGA and identify places to streamline / polish
"""

from typing import List

from niagads.csv_parser.core import CSVFileParser
from niagads.database.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.database.genomicsdb.schema.gene.xrefs import GeneIdentifierType
from niagads.database.genomicsdb.schema.reference.pathway import Pathway
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)
from niagads.genomicsdb_etl.plugins.gene.pathways.base_pathway_plugin import (
    PathwayMembershipLoaderPlugin,
    PathwayMembershipLoaderPluginParams,
)
from niagads.genomicsdb_etl.plugins.gene.pathways.types import (
    MembershipAnnotation,
    PathwayGeneAssociations,
    PathwayInfo,
)
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import (  # TODO: EGA - make wrappers
    MultipleResultsFound,
    NoResultFound,
)

from .helpers import load_pathway
from .types import PathwayAnnotation


class ReactomeEntry(BaseModel):
    gene_id: str
    pathway_id: str
    pathway_url: str
    pathway_name: str
    evidence_code: str
    species: str

    @classmethod
    def column_names(cls):
        return list(cls.model_fields.keys())


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
    validate_file_exists = PathValidatorMixin.validator("file")

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
        if len(ReactomeEntry.column_names()) != len(values):
            raise ValueError(
                f"Expected {len(ReactomeEntry.column_names())} columns, found {len(values)} columns.\n"
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

        # Read into DataFrame with no header and assign column names
        df = parser.to_pandas_df(header=ReactomeEntry.column_names())

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

        # transform data frame to json (list of objects) and use list comprehension to iterate over the objects
        # and build a list of ReactomeEntries
        return [ReactomeEntry(**entry) for entry in filtered_df.to_dict(orient="dict")]

    def transform(self, data: list[ReactomeEntry]) -> list[PathwayGeneAssociations]:
        """
        Transforms the list of ReactomeEntries into a list of PathwayGeneAssociations.


        Args:
            data: Extracted data as a list of dictionaries.

        Returns:
            List[PathwayGeneAssociations]: Transformed data
        """
        self.logger.debug(f"Starting transformation with {len(data)} input rows")

        # Step1 -> initialize an empty hash for PathwayGeneAssociations
        # pathway_id : PathwayGeneAssociation

        transformed = []
        for record in data:
            # Step 2: is record.pathway_id in the hash?
            # if no -> build the PathwayGeneAssociation object for it & add it hash
            # if yes -> create new MembershipAnnotation and add to the member_gene list
            # NOTE: python always updates objects by reference

            # Create PathwayInfo object
            pathway_info = PathwayInfo(
                pathway_id=record["pathway_id"],
                pathway_name=record["pathway_name"],
            )

            # Create MembershipAnnotation object
            genes = [
                MembershipAnnotation(
                    gene_id=record["gene_id"],
                    # include evidence code?
                )
            ]

            # EGA Hint -> don't need this
            # Create PathwayGeneAssociations object
            transformed.append(
                PathwayGeneAssociations(
                    pathway_info=pathway_info,
                    genes=genes,
                )
            )

        # step 4 -> after iterating over the entries - what to return?
        # return the hash the values

        self.logger.info(f"Transformation complete with {len(transformed)} records")
        return transformed

    async def load(self, session, transformed: List[PathwayGeneAssociations]):
        """
        Load transformed records into the database.

        Args:
            session: Database session.
            transformed: List of transformed pathway annotations.

        Returns:
            ResumeCheckpoint: The checkpoint for resuming the ETL process.
        """
        checkpoint = await self._load_pathway_membership(
            session, transformed, GeneIdentifierType.ENSEMBL
        )
        return checkpoint

    def get_record_id(self, record: PathwayGeneAssociations) -> str:
        """
        Get unique identifier for a record.

        Uses combination of pathway_id and gene_id as unique identifier.

        Args:
            record: PathwayGeneAssociations object

        Returns:
            str: Unique identifier
        """
        return f"{record.pathway_info.pathway_id}:{record.associated_genes[0].gene_id}"
