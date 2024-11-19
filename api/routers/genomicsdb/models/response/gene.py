from pydantic import ConfigDict, Field
from sqlmodel import SQLModel
from typing import Optional, List

from api.models import PagedResponseModel, GenericDataModel

class Gene(SQLModel, GenericDataModel):
    ensembl_id: str
    symbol: str
    product: str
    location: str
    type: str
    
    # GVC status
    # exons
    # go terms
    # pathways


