"""model mixins"""

from typing import Any, Dict, List, Self


from pydantic import ConfigDict, Field


class DynamicMixin:
    """A model that allows for extra, unknown fields."""

    __pydantic_extra__: Dict[str, Any]
    model_config = ConfigDict(extra="allow")


class ORMCompatabileMixin:
    """A model that allows being built from SQLAlchemy ORM model"""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @classmethod
    def orm_to_dict(cls, orm_obj):
        """
        makes the dict version of the ORM model-defined object available if need to extract
        or manipulate fields
        """

        orm_obj = orm_obj.model_dump()

        # filter out unused fields expected by the model,
        # making sure to keep any counts as
        # allowable model extras (so that we don't populate alot of
        # unallowed extras)
        fields = cls.get_model_fields()
        return {
            k: v
            for k, v in orm_obj.items()
            if k in fields or (k.startswith("num_") or k == "counts")
        }


class CountsMixin:
    count: int = Field(
        title="Count",
        description="number of matching records or hits in a data track",
    )

    @staticmethod
    def sort(results: List[Self], reverse=True) -> List[Self]:
        """sorts a list of results"""
        return sorted(results, key=lambda item: item.count, reverse=reverse)


class VCFSerializationMixin:
    def to_vcf(self):
        pass


class BEDSerializationMixin:
    def to_bed(self):
        # get valid model fields, make sure they include genomic region or chrm, start, end etc
        # print header
        # for each row in data, print row w/bed fields
        pass
