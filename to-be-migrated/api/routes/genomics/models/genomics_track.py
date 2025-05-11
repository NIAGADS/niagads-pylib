import json
from typing import Any, List, Optional
from os.path import basename

from niagads.utils.list import find

from api.common.enums.response_properties import OnRowSelect, ResponseView

from api.common.formatters import id2title
from api.config.urls import URLS
from api.models.base_response_models import PagedResponseModel
from api.models.track import GenericTrack, GenericTrackSummary
from api.models.track_properties import (
    BiosampleCharacteristics,
    DSSAccession,
    ExperimentalDesign,
)
from api.models.view_models import LinkDataCell, TextDataCell, TextListDataCell
from api.routes.genomics.models.genomics_track_properties import Phenotype, StudyGroup


class GenomicsTrack(GenericTrack):
    description: str
    provenance: DSSAccession
    cohorts: Optional[List[str]] = None
    study_groups: Optional[List[StudyGroup]] = None
    phenotypes: Optional[Phenotype] = None
    covariates: Optional[str] = None

    # FIXME: handle null nested objects in table view

    def get_field_names(self, **kwargs):
        fields = list(self.model_fields.keys())
        fields.remove("data_source")  # will be added back in w/accession
        fields += list(BiosampleCharacteristics.model_fields.keys())
        fields += list(DSSAccession.model_fields.keys())
        fields += list(ExperimentalDesign.model_fields.keys())

        if self.data_category == "QTL":
            # fields += list(ExperimentalDesign.model_fields.keys())
            fields.remove("covariates")
            fields.remove("study_groups")
            fields.remove("experimental_design")
            fields.remove("biosample_characteristics")
            fields.remove("provenance")
            # fields.remove('biosample_term_id')
            fields.remove("cohorts")
        else:
            fields += list(Phenotype.model_fields.keys())

        fields.remove("download_url")
        fields.remove("release_date")
        fields.remove("phenotypes")

        return fields

    def to_view_data(self, view: ResponseView, **kwargs):
        data = super().to_view_data(view, promoteObjs=True)
        # FIXME: handle dictonary cell types on table side of things
        if "study_groups" in data and data["study_groups"] is not None:
            data["study_groups"] = json.dumps(data["study_groups"])

        # FIXME: getting Input should be a subclass of DataCell [type=is_subclass_of, input_value=TextListDataCell(type=('t...'black', tooltip=None)]), input_type=TextListDataCell]\n
        # even though TextListDataCell is a subtype of DataCell
        if "cohorts" in data and data["cohorts"] is not None:
            data["cohorts"] = " // ".join(data["cohorts"])
            # data['cohorts'] = TextListDataCell(items=[TextDataCell(value=c) for c in data['cohorts']])

        # FIXME: how does it end up as an empty string?
        if data["pubmed_id"] != "":
            data["pubmed_id"] = None
        if data["pubmed_id"] is not None:
            data["pubmed_id"] = LinkDataCell(
                value=data["pubmed_id"],
                url=f'{URLS.pubmed}/{data['pubmed_id'].replace("PMID:", "")}',
            )

        # FIXME: Badge?
        if data["url"] is not None:
            data["url"] = LinkDataCell(url=data["url"])

        del data["download_url"]
        del data["release_date"]

        if self.data_category == "QTL":
            del data["experimental_design"]
            del data["cohorts"]
            del data["phenotypes"]
            del data["study_groups"]
            del data["covariates"]
            del data["biosample_term_id"]

        return data

    def get_view_config(self, view: ResponseView, **kwargs):
        """get configuration object required by the view"""
        match view:
            case view.TABLE:
                return self.__build_table_config()
            case _:
                raise NotImplementedError(
                    f"View `{view.value}` not yet supported for this response type"
                )

    def __build_table_config(self):
        """Return a column object for niagads-viz-js/Table"""
        fields = self.get_field_names()
        columns: List[dict] = [{"id": f, "header": id2title(f)} for f in fields]

        # update type of is_lifted to boolean
        index: int = find(columns, "is_lifted", "id", returnValues=False)
        columns[index[0]].update(
            {
                "type": "boolean",
                "description": "data have been lifted over from an earlier genome build",
            }
        )

        # update url to link
        index: int = find(columns, "url", "id", returnValues=False)
        columns[index[0]].update(
            {"type": "link", "canFilter": "false", "disableGlobalFilter": "true"}
        )

        index: int = find(columns, "pubmed_id", "id", returnValues=False)
        columns[index[0]].update({"type": "link"})

        defaultColumns = ["track_id", "name", "feature_type", "biosample_term", "url"]
        options = {"defaultColumns": defaultColumns}

        return {"columns": columns, "options": options}


class GenomicsTrackSummaryResponse(PagedResponseModel):
    data: List[GenericTrackSummary]

    def to_text(self, format: ResponseView, **kwargs):
        fields = (
            self.response[0].get_field_names()
            if len(self.response) > 0
            else GenericTrackSummary.get_model_fields()
        )
        return super().to_text(format, fields=fields)


class GenomicsTrackResponse(PagedResponseModel):
    data: List[GenomicsTrack]

    def to_text(self, format: ResponseView, **kwargs):
        fields = GenomicsTrack.get_model_fields()
        return super().to_text(format, fields=fields)
