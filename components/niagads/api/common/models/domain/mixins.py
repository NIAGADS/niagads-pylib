"""model mixins"""

from typing import Any, Dict, List, Self, Union

from niagads.common.models.base import CustomBaseModel
from niagads.utils.dict import promote_nested
from pydantic import ConfigDict, Field, model_validator


class DynamicMixin:
    """A model that allows for extra, unknown fields."""

    __pydantic_extra__: Dict[str, Any]
    model_config = ConfigDict(extra="allow")


class ORMCompatabileMixin:
    """A model that allows being built from SQLAlchemy ORM model"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def promote_nested(cls: CustomBaseModel, data: Union[Dict[str, Any], Any]):
        """
        summary models can
            1) ignore a subset of the ORM model fields and
            2) expect promotion of some nested fields
        """

        # if not a summary model, skip
        if not getattr(cls.model_config, "is_summary", False):
            return data

        if not isinstance(data, dict):
            try:  # assume data is an ORM w/model_dump mixin
                data = data.model_dump()
            except:  # not a dict or ORM model
                # got here b/c of FAST-API serialization order, so just skip
                return data

        promote_nested(data, modify_in_place=True)

        # filter out unused fields expected by the model,
        # making sure to keep any counts (`num_` fields) as
        # allowable model extras
        fields = cls.get_model_fields()
        return {k: v for k, v in data.items() if k in fields or k.startswith("num_")}


class ResultMetricsMixin:
    num_results: int = Field(
        title="Num. Results",
        description="number of search results",
    )

    @staticmethod
    def sort(results: List[Self], reverse=True) -> List[Self]:
        """sorts a list of results"""
        return sorted(results, key=lambda item: item.num_results, reverse=reverse)
