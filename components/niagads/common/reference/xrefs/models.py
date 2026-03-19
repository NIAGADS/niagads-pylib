from typing import Optional, Union
from niagads.common.models.base import CustomBaseModel
from niagads.utils.regular_expressions import RegularExpressions
from niagads.utils.string import dict_to_info_string, matches
from pydantic import Field, field_validator, model_validator


class ExternalDatabaseRef(CustomBaseModel):
    name: str = Field(title="Data Source Name")
    version: str = Field(title="Data Source Version")


class Pathway(CustomBaseModel):
    """
    Represents a pathway membership annotation for a gene
    """

    id: str = Field(title="Pathway ID")
    pathway: str = Field(title="Pathway")
    xdbref: ExternalDatabaseRef = Field(
        title="Source", description="data source for the pathway annotation"
    )
