"""
Updated Reactome Plugin Code
"""
"""
TODOs:

* remove bad (not unused, but bad) imports
* clean up the logging statements, review them and make sure info, vs debug, vs "verbose"
   * add a temporary critical logging statement in extract to make sure dataframe header is as expected
* remove unused imports
* review w/EGA and identify places to streamline / polish
"""
from typing import List
from niagads.common.types import ETLOperation
from niagads.csv_parser.core import CSVFileParser
from niagads.database.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.database.genomicsdb.schema.reference.pathway import Pathway
from niagads.etl.plugins.parameters import PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.gene.pathways.base_pathway_plugin import PathwayMembershipLoaderPlugin, PathwayMembershipLoaderPluginParams
from niagads.genomicsdb_etl.plugins.gene.pathways.types import MembershipAnnotation, PathwayGeneAssociations, PathwayInfo
from pydantic import BaseModel, Field, field_validator
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.database.genomicsdb.schema.gene.xrefs import GeneIdentifierType

# Removed unused imports and bad imports
# Removed sqlalchemy.exc imports and other unused imports

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


class ReactomeLoaderParams(PathwayMembershipLoaderPluginParams):
    """Parameter model for ReactomeLoader plugin."""

    file: str = Field(..., description="Reactome CSV file to load")

    validate_file_exists = PathValidatorMixin.validator("file")

    @field_validator("file", mode="before")
    def validate_format(cls, file_name: str) -> str:
        """
        Validates that the CSV file has the expected number of columns.
        """
        with open(file_name, "r", encoding="utf-8", errors="ignore") as fh:
            first_line = fh.readline().strip()
            values = first_line.split("\t")

        if len(ReactomeEntry.column_names()) != len(values):
            raise ValueError(
                f"Expected {len(ReactomeEntry.column_names())} columns, found {len(values)} columns.\n"
            )

        if not values[2].startswith("https:"):
            raise ValueError(
                f"Column 3 (pathway_url) should start with 'https:', found: '{values[2]}'\n"
            )

        return file_name

metadata = PluginMetadata(
    version="1.0",
    description=("ETL Plugin to load REACTOME pathway data from file."),
    affected_tables=[PathwayMembership, Pathway],
    load_strategy=ETLLoadStrategy.BATCH,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=ReactomeLoaderParams,
    )

@PluginRegistry.register(metadata=metadata)
class ReactomeLoaderPlugin(PathwayMembershipLoaderPlugin):
    """
    Plugin for loading Reactome data.
    """

    _params: ReactomeLoaderParams


    def extract(self):
        """
        Extract Reactome data from file.
        """
        self.logger.info(f"Parsing Reactome file: {self._params.file}")
        parser = CSVFileParser(self._params.file)
        df = parser.to_pandas_df(names=ReactomeEntry.column_names(),header=None,delimiter="\t")
        self.logger.info(f"File loaded with {len(df)} rows and {len(df.columns)} columns")
       

        filtered_df = df[df["species"] == "Homo sapiens"]
        filtered_df = filtered_df[filtered_df["gene_id"].str.startswith("ENSG", na=False)]

        if self._verbose:
            exact = int(filtered_df.duplicated(keep=False).sum())
            pair = int(
                filtered_df.duplicated(subset=["pathway_id", "gene_id"], keep=False).sum()
            )
            # are there exact duplicate rows and are there pathway/gene repeats with different annotations?
            self.logger.debug("Reactome has exact duplicate rows: %s", exact > 0)
            self.logger.debug(
                "Reactome has pathway/gene repeats with differing annotations: %s", (pair - exact) > 0
            )

        self.logger.info(f"Data extraction complete with {len(filtered_df)} filtered rows")
        return [ReactomeEntry(**entry) for entry in filtered_df.to_dict(orient="records")]

    async def transform(
        self, data: list[ReactomeEntry]
    ) -> list[PathwayGeneAssociations]:
        """
        Transforms the list of ReactomeEntries into a list of PathwayGeneAssociations.
        """
        self.logger.info(f"Starting transformation with {len(data)} input rows")
        duplicate_pair = set() #to track the pathway_id,gene_id pairs
        duplicates_removed = 0
        pathway_map = {}
        for record in data:
            pair = (record.pathway_id, record.gene_id)
            if pair not in duplicate_pair:
                duplicate_pair.add(pair) 
            pathway_id = record.pathway_id
            if pathway_id not in pathway_map:
                pathway_map[pathway_id] = PathwayGeneAssociations(
                    pathway_info=PathwayInfo(
                        pathway_id=record.pathway_id,
                        pathway_name=record.pathway_name,
                    ),
                    member_genes=[],
                )
            pathway_map[pathway_id].member_genes.append(
                MembershipAnnotation(
                    gene_id=record.gene_id,
                    #TODO: Include evidence code if needed
                )
            )
        else: 
            duplicates_removed += 1

        transformed = list(pathway_map.values())
        self.logger.info(f"Transformation complete with {len(transformed)} records and {duplicates_removed} duplicates removed.")
        return transformed

    async def load(self, session, transformed: List[PathwayGeneAssociations]):
        """
        Load transformed records into the database.    """
        checkpoint = await self._load_pathway_membership(
            session, transformed, GeneIdentifierType.ENSEMBL
        )
        return checkpoint

    def get_record_id(self, record: PathwayGeneAssociations) -> str:
        """
        Get unique identifier for a record.
        """
        return f"{record.pathway_info.pathway_id}:{record.genes[0].gene_id}"