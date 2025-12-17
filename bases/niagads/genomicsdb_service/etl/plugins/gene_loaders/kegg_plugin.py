from typing import List
import pandas as pd
from pydantic import Field, field_validator
import xml.etree.ElementTree as ET
from niagads.common.models.composite_attributes.gene import PathwayAnnotation
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.genomicsdb.models.admin.pipeline import ETLOperation


class KEGGLoaderParams(BasePluginParams, PathValidatorMixin):
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

    

class KEGGLoaderPlugin(AbstractBasePlugin):
    """
    Loads KEGG pathway annotations from KGML XML files.
    """

    _params: KEGGLoaderParams

    @classmethod
    def description(cls):
        return "Loads KEGG pathway data from KGML XML files."

    @classmethod
    def parameter_model(cls):
        return KEGGLoaderParams

    @property
    def operation(self):
        return ETLOperation.INSERT

    @property
    def streaming(self):
        return False

    def extract(self):
        file_path = self._params.file
        self.logger.debug(f"Parsing KEGG KGML file: {file_path}")

        
        tree = ET.parse(file_path)
        root = tree.getroot()

        
        raw_name = root.attrib.get("name", "")  # "path:hsa01230"
        pathway_id = raw_name.split(":", 1)[1] if ":" in raw_name else raw_name

        species = root.attrib.get("org", "")          # "hsa"
        pathway_name = root.attrib.get("title", "")   # pathway human name
        pathway_url = f"https://www.kegg.jp/pathway/{pathway_id}"

        annotations: List[PathwayAnnotation] = []

        # Extract gene
        for entry in root.findall("entry"):


                annotation = PathwayAnnotation(
                    gene_id=ncbi_gene_id,
                    pathway_id=pathway_id,
                    pathway_url=pathway_url,
                    pathway_name=pathway_name,
                    evidence_code="KEGG",
                    species=species,
                )

                annotations.append(annotation)

        self.logger.info(
            f"Extracted {len(annotations)} KEGG PathwayAnnotation records from pathway {pathway_id}"
        )

        yield annotations

    def transform(self, data: List[PathwayAnnotation]):
        self.logger.debug("Transform step skipped (KEGG already transformed in extract).")
        return data
    
    async def load(self, transformed: List[PathwayAnnotation], _mode):
        self.logger.debug(f"Loading {len(transformed)} KEGG annotation records")
        return len(transformed)

    def get_record_id(self, record: dict):
        return f"{record['pathway_id']}:{record['gene_id']}"