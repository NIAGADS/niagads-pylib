from typing import List

from fastapi.encoders import jsonable_encoder
from niagads.dict_utils.core import prune


from pydantic import BaseModel, model_serializer


class NullFreeModel(BaseModel):
    @model_serializer()
    def serialize_model(self, values, **kwargs):
        return prune(dict(self), removeNulls=True)


class SerializableModel(BaseModel):
    def serialize(
        self,
        exclude: List[str] = None,
        promoteObjs=False,
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
            objFields = [k for k, v in data.items() if isinstance(v, dict)]
            for f in objFields:
                data.update(data.pop(f, None))

        if collapseUrls:
            fields = list(data.keys())
            pairedFields = [f for f in fields if f + "_url" in fields]
            for f in pairedFields:
                data.update({f: {"url": data.pop(f + "_url", None), "value": data[f]}})

        if groupExtra:
            raise NotImplementedError()

        return data
