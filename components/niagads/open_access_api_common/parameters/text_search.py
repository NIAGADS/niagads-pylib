from abc import ABC, abstractmethod
from fastapi import Query
from niagads.enums.core import CaseInsensitiveEnum
from niagads.exceptions.core import ValidationError
from niagads.exceptions.core import extract_exception_message
from niagads.open_access_api_common.parameters.expression_filter import FilterParameter
from niagads.utils.string import sanitize
from pyparsing import (
    Combine,
    Dict,
    Group,
    Keyword,
    NotAny,
    OneOrMore,
    Word,
    ZeroOrMore,
    alphas,
)
from pyparsing.helpers import one_of
from sqlmodel import col, not_


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


class TextSearchFilterParameter(FilterParameter):
    def __init__(self, fields: CaseInsensitiveEnum):
        super().__init__(fields)

    def _set_grammar(self):
        field = Word(alphas + "_").set_results_name(
            "field"
        )  # Fields like "data_source" or "biosample"

        operator = (
            Keyword("eq") | Keyword("neq") | Keyword("like") | Keyword("not like")
        ).set_results_name(
            "operator"
        )  # Operators

        # TODO: keyword `or`
        _join = (Keyword("and")).set_results_name("boolean")  # Logical operators

        value = (
            OneOrMore(~_join + Word(alphas))
            .add_parse_action(" ".join)
            .set_results_name("value")
        )

        # Define the grammar for a single condition
        condition = Group(field + operator + value)
        # Define the full grammar for the boolean expression
        self._grammar = condition + ZeroOrMore(_join + condition)


async def keyword_param(
    keyword: str = Query(
        default=None,
        description="Search all text annotations by keyword.  Matches are exact and case-sensitive.",
    )
) -> str:
    if keyword is not None:
        return sanitize(keyword)
    return keyword
