"""Common Pydantic `Models` for the Open Access API services

includes the following:

* core: foundational models for most data and response models
* responses: response models and models defining response model properities or configuration
* data: core representation of API responses as table row of one or more records
* sql:

"""

from typing import List

from fastapi.encoders import jsonable_encoder
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.dict import promote_nested
from pydantic import BaseModel


class Entity(CaseInsensitiveEnum):
    GENE = "gene"
    VARIANT = "variant"
    SPAN = "span"
    TRACK = "track"

    def __str__(self):
        return self.value.title()


class SerializableModel(BaseModel):
    """a pydantic model w/custom serialization that handles:
    * promotion of nested JSON attribute to the top level
    * url/value pairs
    * grouping of extra fields (not yet implemented)
    * aliased field names
    """

    def serialize(
        self,
        exclude: List[str] = None,
        promoteObjs=False,  # FIXME: provide optional list of which objects to promote
        collapseUrls=False,
        groupExtra=False,
        byAlias=False,
    ):
        """
        basically a customized `model_dumps` but only when explicity called
        returns a dict which contains only serializable fields.
        exclude -> list of fields to exclude
        promoteObjs -> when True expands JSON fields; i.e., ds = {a:1, b:2} becomes a:1, b:2 and ds gets dropped
        collapseUrls -> looks for field and field_url pairs and then updates field to be {url: , value: } object
        groupExtra -> if extra fields are present, group into a JSON object
        """
        # note: encoder is necessary to correctly return enums/dates, etc
        data: dict = jsonable_encoder(
            self.model_dump(exclude=exclude, by_alias=byAlias)
        )
        # FIXME: does not handle case if the dict field is null (e.g., experimental_design on genomics tracks)
        if promoteObjs:
            promote_nested(data, updateByReference=True)

        if collapseUrls:
            fields = list(data.keys())
            pairedFields = [f for f in fields if f + "_url" in fields]
            for f in pairedFields:
                data.update({f: {"url": data.pop(f + "_url", None), "value": data[f]}})

        if groupExtra:
            raise NotImplementedError()

        return data
