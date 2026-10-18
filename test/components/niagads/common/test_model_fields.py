import pytest
from niagads.common.models.base import CustomBaseModel
from pydantic import ConfigDict, Field


class OrderedRecord(CustomBaseModel):
    model_config = ConfigDict(extra="allow")

    unranked: str = "unranked"
    second: str = Field(default="second", json_schema_extra={"order": 2})
    first: str = Field(default="first", json_schema_extra={"order": 1})
    excluded: str = Field(default="excluded", exclude=True)


@pytest.mark.parametrize(
    "sort, expected",
    [
        (False, ["unranked", "second", "first"]),
        (True, ["first", "second", "unranked"]),
    ],
)
def test_model_field_order(sort, expected):
    assert OrderedRecord.get_model_fields_from_class(sort=sort) == expected
    assert OrderedRecord().get_model_fields(sort=sort) == expected


def test_sorted_model_fields_append_extras():
    record = OrderedRecord(extra_value="extra")

    assert record.get_model_fields(sort=True) == [
        "first",
        "second",
        "unranked",
        "extra_value",
    ]
    assert record.to_value_list() == ["first", "second", "unranked", "extra"]
