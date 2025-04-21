from datetime import date
from typing import List, Optional

from niagads.open_access_api_configuration.resource_links import DATASOURCE_URLS
from niagads.open_access_api_models.core import NullFreeModel
from niagads.string_utils.regular_expressions import RegularExpressions
from pydantic import BaseModel, Field, computed_field
from sqlalchemy import Null
from zmq import PUB


class ExperimentalDesign(NullFreeModel):
    antibody_target: Optional[str] = None
    assay: Optional[str] = None
    analysis: Optional[str] = None
    classification: Optional[str] = None
    data_category: Optional[str] = None
    output_type: Optional[str] = None
    is_lifted: Optional[bool] = False


class BiosampleCharacteristics(NullFreeModel):
    system: Optional[str] = None
    tissue: Optional[str] = None
    biosample_term: Optional[str] = Field(
        default=None, description="mapped ontology term"
    )
    biosample_term_id: Optional[str] = Field(
        default=None, description="mapped ontology term identifier"
    )
    life_stage: Optional[str] = Field(
        default=None, description="donor/sample life stage: adult, fetal, embryo"
    )


class Provenance(NullFreeModel):
    data_source: str
    data_source_version: Optional[str] = None

    download_date: Optional[date] = None
    download_url: Optional[str] = None

    release_date: Optional[date] = None

    study_or_project: Optional[str] = None
    accession: str
    pubmed_id: Optional[str] = Field(regex=RegularExpressions.PUBMED_ID, default=None)
    doi: Optional[str] = Field(regex=RegularExpressions.DOI, default=None)
    consortia: Optional[str] = None
    attribution: Optional[str] = None

    @computed_field
    @property
    def data_source_url(self) -> str:
        dsKey = (
            self.data_source + "|" + self.data_source_version
            if self.data_source_version is not None
            else self.data_source
        )
        try:
            return getattr(DATASOURCE_URLS, dsKey)

        except KeyError:
            raise KeyError(
                f"Data source URL not found for {dsKey}. Please add to DATASOURCE_URLS."
            )


class FileProperties(NullFreeModel):
    file_name: Optional[str] = None
    url: Optional[str] = None
    md5sum: Optional[str] = Field(regex=RegularExpressions.MD5SUM, default=None)

    bp_covered: Optional[int] = None
    number_of_intervals: Optional[int] = None
    file_size: Optional[int] = None

    file_format: Optional[str] = None
    file_schema: Optional[str] = None
    release_date: Optional[date] = None
