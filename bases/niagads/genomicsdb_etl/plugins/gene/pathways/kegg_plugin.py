import xml.etree.ElementTree as ET
from typing import List

from niagads.genomicsdb_etl.plugins.common.mixins.parameters import (
    ExternalDatabaseRefMixin,
)

from niagads.common.gene.models.annotation import PathwayMembership
from niagads.common.reference.xrefs.data_sources import ThirdPartyResources
from niagads.common.reference.xrefs.models import Pathway
from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.xrefs import GeneXRefType
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import (
    BasePluginParams,
    PathValidatorMixin,
    ResumeCheckpoint,
)
from niagads.etl.plugins.registry import PluginRegistry
from niagads.genomicsdb_etl.plugins.gene.pathways.helpers import load_pathway
from niagads.genomicsdb_etl.plugins.gene.pathways.types import GenePathwayAssociation
from pydantic import Field, field_validator


from niagads.etl.plugins.types import ETLLoadStrategy


class KEGGLoaderParams(BasePluginParams, PathValidatorMixin, ExternalDatabaseRefMixin):
    """
    Parameters for KEGGLoaderPlugin.
    """

    file: str = Field(..., description="KEGG KGML XML file to load")

    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)

    @field_validator("file", mode="before")
    def validate_format(cls, file_name: str) -> str:
        """
        Ensure KGML begins with <pathway>.
        Skips comments and blank lines.
        """
        with open(file_name, "r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped and not stripped.startswith("<!--"):
                    first_tag = stripped
                    break
            else:
                raise ValueError("KGML file is empty or contains no valid lines.")

        if not first_tag.startswith("<pathway"):
            raise ValueError(f"KGML must begin with <pathway>, got: {first_tag[:50]}")

        return file_name


metadata = PluginMetadata(
    version="1.0",
    description=("ETL Plugin to load KEGG pathway data from KGML XML files."),
    affected_tables=[PathwayMembership, Pathway],
    load_strategy=ETLLoadStrategy.CHUNKED,
    operation=ETLOperation.INSERT,
    is_large_dataset=False,
    parameter_model=KEGGLoaderParams,
)


@PluginRegistry.register(metadata=metadata)
class KEGGLoaderPlugin(AbstractBasePlugin):
    """
    Loads KEGG pathway annotations from KGML XML files.
    """

    _params: KEGGLoaderParams

    @property
    def external_database_id(self):
        return self.__external_database.external_database_id

    async def on_run_start(self, session):
        """on run start hook override"""

        # validate the xdbref against the database
        self.__external_database: ExternalDatabase = (
            await self._params.fetch_xdbref(session) if self.is_etl_run else None
        )

        self.logger.debug(
            f"external_database_id = {self.__external_database.external_database_id}"
        )

    def extract(self):
        file_path = self._params.file
        self.logger.debug(f"Parsing KEGG KGML file: {file_path}")

        tree = ET.parse(file_path)
        root = tree.getroot()

        raw_name = root.attrib.get("name", "")  # "path:hsa01230"
        pathway_id = raw_name.split(":", 1)[1] if ":" in raw_name else raw_name

        pathway_name = root.attrib.get("title", "")  # pathway name

        # Find and parse gene entries
        for entry in root.findall("entry"):
            annotation = GenePathwayAssociation(
                gene_id=entry.attrib.get("id"),
                pathway_id=pathway_id,
                pathway_name=pathway_name,
            )

            if self._verbose:
                self.logger.debug(f"Extracted: {annotation.model_dump()}")

            yield annotation

    def transform(self, data: GenePathwayAssociation):
        # no transform necessary; GeenPathwayAssociation already object generated in Extract
        return data

    async def load(self, session, transformed: List[GenePathwayAssociation]):
        """
        Load transformed records into the database.
        """
        checkpoint = await load_pathway(self, session, transformed, GeneXRefType.NCBI)
        return checkpoint

    def get_record_id(self, record: dict):
        return f"{record['pathway_id']}:{record['gene_id']}"
