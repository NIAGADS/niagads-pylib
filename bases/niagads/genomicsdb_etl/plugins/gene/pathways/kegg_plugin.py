import xml.etree.ElementTree as ET
from typing import List, Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.database.genomicsdb.schema.gene.xrefs import GeneIdentifierType
from niagads.database.genomicsdb.schema.reference.pathway import Pathway
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.genomicsdb_etl.plugins.gene.pathways.base_pathway_plugin import (
    PathwayMembershipLoaderPlugin,
    PathwayMembershipLoaderPluginParams,
)
from niagads.genomicsdb_etl.plugins.gene.pathways.types import GenePathwayAssociation
from niagads.utils.sys import get_files_by_pattern
from pydantic import Field


class KEGGLoaderParams(PathwayMembershipLoaderPluginParams):
    """
    Parameters for KEGGLoaderPlugin.
    """

    kgml_dir: str = Field(
        ..., description="directory containing KEGG KGML XML files to load"
    )

    validate_file_exists = PathValidatorMixin.validator("kgml_dir")


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
class KEGGLoaderPlugin(PathwayMembershipLoaderPlugin):
    """
    Loads KEGG pathway annotations from KGML XML files.
    """

    _params: KEGGLoaderParams

    def extract(self):
        files: List[str] = get_files_by_pattern(self._params.kgml_dir, "*.kgml")
        self.logger.info(f"Found {len(files)} KGML Files to load.")

        for file_path in files:
            self.logger.info(f"Parsing: {file_path}")

            tree = ET.parse(file_path)
            root = tree.getroot()

            raw_name = root.attrib.get("name", "")  # "path:hsa01230"
            pathway_id = raw_name.split(":", 1)[1] if ":" in raw_name else raw_name
            pathway_name = root.attrib.get("title", "")  # pathway name

            if self._verbose:
                self.logger.info(f"Pathway: {pathway_id}:{pathway_name}")

            # <entry id="758" name="hsa:27235" type="gene" reaction="rn:R05000" link="https://www.kegg.jp/dbget-bin/www_bget?hsa:27235">
            #    <graphics name="" .../>
            # </entry>

            # Find and parse gene entries; need to filter for type="gene"
            annotations = [
                GenePathwayAssociation(
                    gene_id=entry.attrib.get("id"),
                    pathway_id=pathway_id,
                    pathway_name=pathway_name,
                )
                for entry in root.findall("entry[@type='gene']")
            ]

            self.logger.debug(f"Extracted: {len(annotations)} gene-pathway memberships")

            yield annotations

    def transform(self, data: List[GenePathwayAssociation]):
        # no transform necessary; GeenPathwayAssociation already object generated in Extract
        return data

    async def load(self, session, transformed: List[GenePathwayAssociation]):
        """
        Load transformed records into the database.
        """
        checkpoint = await self._load_pathway_membership(
            session, transformed, GeneIdentifierType.NCBI
        )
        return checkpoint
