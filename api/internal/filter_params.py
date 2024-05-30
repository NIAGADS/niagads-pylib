from fastapi import Query
from typing import List
from enum import Enum
from niagads.utils.enums import CustomStrEnum

class FilterQueryTypes(str, Enum):
    RANGE = "range"
    LOGICAL = "logical"
    ALL = "all"

class FilterQueryOperators(CustomStrEnum):
    """ enum for filter operators"""
    RANGE_GT = "gt"
    RANGE_LT = "lt"
    RANGE_GE = "ge"
    RANGE_LE = "le"
    BOOL_AND = "and"
    BOOL_OR = "or"
    BOOL_NOT = "not"
    RANGE_BOOL_EQUALS = "eq"
    
    @classmethod
    def logical(self):
        """ return a list of logical operators """
        return [e.value for e in self if 'BOOL' in e.name] 
    
    @classmethod
    def all(self):
        return self.list()
    
    @classmethod
    def range(self):
        return [e.value for e in self if 'RANGE' in e.name]
    
async def filter_param(filter: str = Query(), allowableQueryFields: List[str], operators: []):
    """ filter string param
        e.g., filter=datasource eq ENCODE and assay eq ChIP-Seq 
        
        or
        filter=start gt 50000
    """
    # tokenize
    pass