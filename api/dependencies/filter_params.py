from fastapi import Query
from enum import Enum, auto
from typing import List

from pyparsing import Group, Keyword, OneOrMore, Optional, Word, alphas, nums, ParserElement
from pyparsing.helpers import one_of

from urllib.parse import unquote

from .param_validation import clean
from .exceptions import get_error_message

_NUMBER = Word(nums)
_TEXT = Word(alphas + '+')
_JOIN =  Keyword("and") | Keyword("or")

class ExpressionType(str, Enum):
    """enum for text expression types (text vs numeric)"""
    TEXT = auto()
    RANGE = auto()
    
class FilterParameter():
    def __init__(self, allowableFields: List[str], expressionType: ExpressionType):
        self.__field = one_of(allowableFields, as_keyword=True)
        self.__expressionType = expressionType
        
        
    def __parse_expression(self, expression: str):
        if self.__expressionType == ExpressionType.TEXT:
            return self.__parse_text_expression(expression)
        return self.__parse_numeric_expression(expression)


    def __parse_text_expression(self, expression: str):
        operator = Keyword("like") | Keyword("eq") | Keyword("neq") 
        pattern = Group(self.__field + operator + _TEXT) + Optional(_JOIN)
        return pattern.parseString(expression, parseAll=True)


    def __parse_numeric_expression(self, expression: str):
        operator = Keyword("eq") | Keyword("lt") | Keyword("le") | Keyword("gt") | Keyword("ge") | Keyword("neq") 
        pattern = Group(self.__field + operator + _NUMBER) + Optional(_JOIN)
        return pattern.parseString(expression, parseAll=True)
    
    
    def __call__(self, filter: str=Query(title="description expression string")):
        if filter:
            try:
                return self.__parse_expression(filter)
            except Exception as e:
                raise ValueError(f'Unable to parse `filter` expression: {filter}; {get_error_message(e)}', )
                
        return None
