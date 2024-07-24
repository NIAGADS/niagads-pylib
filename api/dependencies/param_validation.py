import nh3 # XSS protection

from fastapi import Query

from enum import Enum, auto
from pydantic import BaseModel
from typing import Optional, Set, List

from niagads.reference.chromosomes import Human as Chromosome


# TODO: investigate nh3.clean and all its options
def clean(html: str):
    return nh3.clean_text(html)


# https://fastapi.tiangolo.com/tutorial/query-params-str-validations/#query-parameter-list-multiple-values


    