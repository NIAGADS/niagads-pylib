from abc import ABC, abstractmethod
from typing import List

from fastapi import Query
from niagads.enums.core import CaseInsensitiveEnum
from niagads.exceptions.core import ValidationError, extract_exception_message
from pydantic import BaseModel
from pyparsing import Union


class Triple(BaseModel):
    field: str
    operator: str
    value: Union[str, int, float]


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
        triples = [Triple(**(phrase.as_dict())) for phrase in expression]
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
