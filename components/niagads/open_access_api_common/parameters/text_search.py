from enum import Enum, auto

from fastapi import Query
from niagads.exceptions.core import ValidationError
from niagads.exceptions.core import extract_exception_message
from niagads.utils.string import sanitize
from pyparsing import (
    Group,
    Keyword,
    OneOrMore,
    Optional,
    ParserElement,
    Word,
    alphas,
    nums,
)
from pyparsing.helpers import one_of
from sqlmodel import col, not_

_NUMBER = Word(nums)
_TEXT = Word(alphas + "_" + "-")
_JOIN = Keyword("and") | Keyword(";")  # TODO: | Keyword("or")


_OPERATORS = {
    "eq": "`equals`: exact, case sensitive, matches to entire field",
    "neq": "`not equals`: exact, case sensitive, negative matches to entire field",
    "like": "`like`: case-insensitive substring matching; NOTE for queries against `biosample`, `eq` and `neq` will be executed as `like` or `not like`, respeectively",
}


class ExpressionType(str, Enum):
    """enum for text expression types (text vs numeric)"""

    TEXT = auto()
    RANGE = auto()


def tripleToPreparedStatement(triple, model):
    """translate filter triple into prepared statement"""
    field = triple[0].split("|")
    tableField = col(getattr(model, field[0]))
    if len(field) > 1:  # jsonb field
        tableField = tableField[field[1]].astext

    operator = triple[1]
    test = triple[2].replace("_", " ")

    if operator == "eq":
        return tableField == test
    if operator == "neq":
        return not_(tableField == test)
    if operator == "like":
        return tableField.regexp_match(test, "i")
    if operator == "not like":
        return not_(tableField.regexp_match(test, "i"))

    else:
        raise NotImplementedError(
            f"mapping to prepared statement not yet implemented for operator {operator}"
        )


class FilterParameter:
    def __init__(
        self, fieldMap: dict | None = None, expressionType: ExpressionType | None = None
    ):
        self.__field = one_of(list(fieldMap.keys()), as_keyword=True)
        self.__expressionType = expressionType

    def __parse_expression(self, expression: str):
        if self.__expressionType == ExpressionType.TEXT:
            return self.__parse_text_expression(expression)
        return self.__parse_numeric_expression(expression)

    def __parse_text_expression(self, expression: str):
        operator = Keyword("like") | Keyword("eq") | Keyword("neq")
        pattern = OneOrMore(Group(self.__field + operator + _TEXT) + Optional(_JOIN))
        return pattern.parseString(expression, parse_all=True)

    def __parse_numeric_expression(self, expression: str):
        operator = (
            Keyword("eq")
            | Keyword("lt")
            | Keyword("le")
            | Keyword("gt")
            | Keyword("ge")
            | Keyword("neq")
        )
        pattern = OneOrMore(Group(self.__field + operator + _NUMBER) + Optional(_JOIN))
        return pattern.parseString(expression, parse_all=True)

    def __call__(
        self,
        filter: str = Query(
            default=None,
            description="filter expresssion string",
            examples=["datasource eq GTEx and biosample eq brain"],
        ),
    ):
        try:
            if filter is not None:
                return self.__parse_expression(filter).as_list()
            else:
                return None

        except Exception as e:
            raise ValidationError(
                f"Unable to parse `filter` expression: {filter}; {extract_exception_message(e)}.  Example expression: data_source eq GTEx and biosample like astrocyte.  Test conditions must substitute an underscore (_) for spaces, e.g., histone modification should be written as histone_modification"
            )


async def keyword_param(
    keyword: str = Query(
        default=None,
        description="Search all text annotations by keyword.  Matches are exact and case-sensitive.",
    )
) -> str:
    if keyword is not None:
        return sanitize(keyword)
    return keyword
