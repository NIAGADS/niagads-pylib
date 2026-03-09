from typing import List, Optional, Set

from niagads.common.constants.external_resources import (
    Consortia,
    NIAGADSResources,
    ThirdPartyResources,
)
from niagads.common.models.core import TransformableModel
from niagads.common.types import T_PubMedID
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import matches
from pydantic import Field, computed_field, field_validator


class Provenance(TransformableModel):
    data_source: str = Field(
        default=NIAGADSResources.NIAGADS_DSS.name,
        title="Data Source",
        description="original file data source",
    )
    accession: str = Field(
        title="Accession",
        description="accession identifier in original data source; may be parent accession if track is part of a collection (e.g., NIAGADS DSS dataset accession)",
    )  # FIXME: for FILER set to None or figure out where original accession is?
    release_date: str = Field(title="Release Date")
    release_version: Optional[str] = Field(default=None, title="Release Version")
    download_date: Optional[str] = Field(
        default=None,
        title="Download Date",
        json_schema_extra={"is_filer_annotation": True},
    )
    download_url: Optional[str] = Field(
        default=None,
        title="Download URL",
        exclude=True,
        json_schema_extra={"is_filer_annotation": True},
    )
    consortium: Optional[Set[Consortia]] = Field(
        default=None,
        title="Consortium",
        description=f"collaborative partnership; one or more of {Consortia.list()}",
    )
    study: Optional[str] = Field(default=None, title="Study")
    project: Optional[str] = Field(
        default=None,
        title="Project",
        description=(
            "organizational unit that may include multiple studies and datasets "
            "under a common goal, funding source, or program. (e.g., ADSP FunGen xQTL)"
        ),
    )
    attribution: str = Field(
        pattern=RegularExpressions.ATTRIBUTION,
        title="Attribution",
        description="Human-readable author citation for primary publication (or PI and year if no publication), e.g., Naj et al. 2006",
    )  # FIXME: for FILER allow to be None
    pubmed_id: Optional[Set[T_PubMedID]] = Field(default=None, title="PubMed ID")
    doi: Optional[Set[str]] = Field(default=None, title="DOI")

    def _flat_dump(self, nullFree=False, delimiter="|"):
        obj = {
            k: (
                self._list_to_string(list(v), delimiter=delimiter)
                if isinstance(v, set)
                else str(v) if v is not None else v
            )
            for k, v in super()._flat_dump(null_free=nullFree).items()
        }
        return obj

    @field_validator("doi", mode="after")
    def validate_doi(cls, values: Set[str]):
        """create validator b/c Pydantic does not support patterns w/lookaheads"""
        if values is not None and len(values) > 0:
            for v in values:
                if not matches(RegularExpressions.DOI, v):
                    raise ValueError(
                        f"Invalid DOI format: {v}. Please provide a valid DOI."
                    )
        return values

    @computed_field
    @property
    def data_source_url(self) -> str:
        # dsKey: str = (
        #    f"{self.data_source}|{self.release_version}"
        #    if self.release_version is not None
        #    else self.data_source
        # )
        # removed versioning from the data source URLs; incorrect legacy from FILER
        dsKey = self.data_source
        try:
            return ThirdPartyResources(dsKey).value
        except:
            try:
                return NIAGADSResources(dsKey).value
            except:
                raise ValueError(
                    f"Data source URL not found for {dsKey}. Please add to external_resources.ThirdParty."
                )


class FileProperties(TransformableModel):
    file_name: str = Field(title="File Name")
    url: Optional[str] = Field(
        default=None,
        title="URL",
        json_schema_extra={"is_filer_annotation": True},
    )
    md5sum: str = Field(pattern=RegularExpressions.MD5SUM, title="MD5 Sum")

    bp_covered: Optional[int] = Field(
        default=None,
        title="Base Pairs Covered",
        json_schema_extra={"is_filer_annotation": True},
    )
    num_intervals: Optional[int] = Field(
        default=None,
        title="Number of Intervals",
        json_schema_extra={"is_filer_annotation": True},
    )
    file_size: int = Field(title="File Size")

    file_format: Optional[str] = Field(
        default=None,
        title="File Format",
        json_schema_extra={"is_filer_annotation": True},
    )
    file_schema: Optional[str] = Field(
        default=None,
        title="File Schema",
        json_schema_extra={"is_filer_annotation": True},
    )
    release_date: Optional[str] = Field(
        default=None,
        title="Release Date",
        json_schema_extra={"is_filer_annotation": True},
    )  # Field(exclude=True)
