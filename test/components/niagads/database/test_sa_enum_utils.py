from niagads.database.sa_enum_utils import enum_column, enum_constraint
from niagads.enums.core import CaseInsensitiveEnum


class EnumA(CaseInsensitiveEnum):
    A1 = "a1"
    A2 = "a2"


class EnumB(CaseInsensitiveEnum):
    B1 = "b1"


def test_enum_column_accepts_single_enum():
    col = enum_column(EnumA)
    values = list(col.type.enums)
    assert values == ["a1", "a2"]


def test_enum_column_accepts_enum_list():
    col = enum_column([EnumA, EnumB])
    values = list(col.type.enums)
    assert values == ["a1", "a2", "b1"]


def test_enum_constraint_accepts_enum_list():
    constraint = enum_constraint("field", [EnumA, EnumB])
    sqltext = str(constraint.sqltext)
    assert "field in" in sqltext
    assert "'a1'" in sqltext
    assert "'a2'" in sqltext
    assert "'b1'" in sqltext
