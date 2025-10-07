from abc import ABC, abstractmethod
from typing import List

from fastapi import Query

from niagads.enums.core import CaseInsensitiveEnum
from niagads.exceptions.core import ValidationError, extract_exception_message
from niagads.utils.string import is_number
from pydantic import BaseModel
from pyparsing import ParseResults, Union
from sqlalchemy import Column


class Triple(BaseModel):
    field: str
    operator: str
    value: Union[str, int, float]

    def to_prepared_statement(self, column: Column):
        """translate filter triple into prepared statement"""

        match self.operator:
            case "eq":
                # use ilike instead of == to allow case insensitive matches
                if is_number(self.value):
                    return column == self.value
                else:
                    return column.ilike(self.value)
            case "neq":
                if is_number(self.value):
                    return column != self.value
                return column.not_ilike(self.value)
            case "like":
                # add in wild cards
                return column.ilike(f"%{self.value}%")
            case "not like":
                return column.not_ilike(f"%{self.value}%")
            case "gt":
                return column > self.value
            case "lt":
                return column < self.value
            case "gte":
                return column >= self.value
            case "lte":
                return column <= self.value
            case _:
                raise NotImplementedError(
                    f"mapping to prepared statement not yet implemented for operator {self.operator}"
                )


class FilterParameter(ABC):
    def __init__(self, fields: CaseInsensitiveEnum):
        self._fields: CaseInsensitiveEnum = fields
        self._grammar = None
        self._set_grammar()

    @abstractmethod
    def _set_grammar(self):
        pass

    def parse_expression(self, text: str) -> dict:
        expression = self._grammar.parseString(text, parse_all=True)
        triples = [
            Triple(**(phrase.as_dict()))
            for phrase in expression
            if isinstance(phrase, ParseResults)
        ]
        self.validate_fields(triples)
        return triples

    def validate_fields(self, triples: List[Triple]):
        # Convert to a dictionary-like structure
        # of field, operator, value
        for t in triples:
            try:
                self._fields(t.field)
            except:
                raise ValidationError(
                    f"Invalid filter field `{t.field}`.  Allowable values are: {self._fields.list(toLower=True)}"
                )

    def __call__(
        self,
        filter: str = Query(default=None, description="filter expresssion string"),
    ):
        try:
            if filter is not None:
                return self.parse_expression(filter)
            else:
                return None

        except Exception as e:
            raise ValidationError(
                f"Unable to parse `filter` expression: {filter.strip()}; {extract_exception_message(e)}."
            )
