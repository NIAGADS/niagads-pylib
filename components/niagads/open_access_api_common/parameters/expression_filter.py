from abc import ABC, abstractmethod

from fastapi import Query
from niagads.enums.core import CaseInsensitiveEnum
from niagads.exceptions.core import ValidationError, extract_exception_message
from pyparsing import Group, ParseResults


class FilterParameter(ABC):
    def __init__(self, fields: CaseInsensitiveEnum):
        self._fields: CaseInsensitiveEnum = fields
        self._grammar = None

    @abstractmethod
    def set_grammar(self):
        pass

    @abstractmethod
    def parse_expression(self, text: str):
        pass

    def validate_expression(self, parsedExpression: ParseResults):
        # Convert to a dictionary-like structure
        # of field, operator, value
        triples = [
            condition.as_dict()
            for condition in parsedExpression
            if isinstance(condition, Group)
        ]
        for t in triples:
            try:
                self._fields(t["field"])
            except:
                raise ValueError(
                    f"Invalid filter field `{t['field']}`.  Allowable values are: {self._fields.list()}"
                )

    def __call__(
        self,
        filter: str = Query(default=None, description="filter expresssion string"),
    ):
        try:
            if filter is not None:
                return self.parse_expression(filter).as_list()
            else:
                return None

        except Exception as e:
            raise ValidationError(
                f"Unable to parse `filter` expression: {filter}; {extract_exception_message(e)}."
            )
