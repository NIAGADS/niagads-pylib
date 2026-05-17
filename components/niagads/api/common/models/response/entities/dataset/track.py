from typing import List
from niagads.api.common.constants import DEFAULT_NULL_STRING
from niagads.api.common.data_models.entities.dataset.track import Track, TrackSummary

from pydantic import ConfigDict, Field


class BaseTrackResponse(RecordResponse):
    model_config = ConfigDict(null_str=DEFAULT_NULL_STRING)


class TrackSummaryResponse(BaseTrackResponse):

    data: List[TrackSummary] = Field(
        description=(
            "Abridged metadata for each track meeting the query criteria."
            "Depending on query may include count of records matching query "
            "parameters (num_results)."
        )
    )


class TrackResponse(BaseTrackResponse):
    model_config = ConfigDict(null_str=DEFAULT_NULL_STRING)
    data: List[Track] = Field(
        description="Full metadata for each track meeting the query criteria."
    )

    def to_text(self, incl_header=False, null_str=DEFAULT_NULL_STRING):
        if self.is_empty():
            if incl_header:
                return self._get_empty_header()
            else:
                return ""

        else:
            fields = self.data[0].get_model_fields(as_str=True)
            rows = []
            for r in self.data:
                if isinstance(r, str):
                    rows.append(r)
                else:
                    # pass fields to ensure consistent ordering
                    rows.append(r.as_text(fields=fields, null_str=null_str))

            response_str = "\t".join(fields) + "\n" if incl_header else ""
            response_str += "\n".join(rows)

        return response_str
