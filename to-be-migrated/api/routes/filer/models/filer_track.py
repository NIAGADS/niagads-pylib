from datetime import date
from sqlmodel import SQLModel
from typing import Optional, List

from niagads.utils.list import get_duplicates

from api.common.enums.response_properties import ResponseView
from api.common.formatters import id2title

from api.models.base_response_models import PagedResponseModel
from api.models.track import GenericTrack, GenericTrackSummary
from api.models.track_properties import BiosampleCharacteristics, ExperimentalDesign
from api.models.database.metadata import FILERAccession

# Developer Note: not setting a default for optionals b/c coming from
# the SQLModel, which will have nulls if no value


# note this is a generic data model so that we can add summary fields (e.g., counts) as needed
class FILERTrackSummary(GenericTrackSummary):
    study_name: Optional[str]
    assay: Optional[str]


class FILERTrack(GenericTrack):
    assay: Optional[str]
    provenance: FILERAccession
    study_name: Optional[str]

    # FILER properties
    file_name: Optional[str]
    index_url: Optional[str]
    md5sum: Optional[str]
    raw_file_url: Optional[str]
    raw_file_md5sum: Optional[str]
    bp_covered: Optional[int]
    number_of_intervals: Optional[int]
    file_size: Optional[int]
    file_format: Optional[str]
    file_schema: Optional[str]

    def get_field_names(self, **kwargs):
        fields = list(self.model_fields.keys())
        fields += list(BiosampleCharacteristics.model_fields.keys())
        fields += list(ExperimentalDesign.model_fields.keys())
        fields += list(FILERAccession.model_fields.keys())

        if self.data_category == "QTL":
            # fields += list(ExperimentalDesign.model_fields.keys())
            if "study_groups" in fields:
                fields.remove("study_groups")
            fields.remove("experimental_design")
            fields.remove("biosample_characteristics")
            fields.remove("provenance")
            # fields.remove('biosample_term_id')

            fields.remove("download_url")
            fields.remove("release_date")
            fields.remove("raw_file_url")
            fields.remove("raw_file_md5sum")

        duplicates = get_duplicates(
            fields
        )  # FIXME: some of the nested fields will be duplicated
        for f in duplicates:
            fields.remove(f)

        return fields

    def get_view_config(self, view: ResponseView, **kwargs):
        return super().get_view_config(view, **kwargs)

    def to_view_data(self, view: ResponseView, **kwargs):
        data = self.serialize(promoteObjs=True, exclude=["replicates"])

        if "field_names" in kwargs:
            dropFields = set(data.keys()).difference(set(kwargs["field_names"]))
            for field in dropFields:
                del data[field]

        return data

    def _build_table_config(self):
        config = super()._build_table_config()
        return config


class FILERTrackSummaryResponse(PagedResponseModel):
    data: List[FILERTrackSummary]

    def to_text(self, format: ResponseView, **kwargs):
        # fields could contain num_results if a result is present
        fields = (
            self.response[0].get_field_names()
            if len(self.response) > 0
            else FILERTrackSummary.get_model_fields()
        )
        return super().to_text(format, fields=fields)


class FILERTrackResponse(PagedResponseModel):
    data: List[FILERTrack]

    def to_text(self, format: ResponseView, **kwargs):
        fields = FILERTrack.get_model_fields()
        return super().to_text(format, fields=fields)
