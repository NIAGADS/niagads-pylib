from typing import Optional
from niagads.common.models.base import CustomBaseModel
from pydantic import Field


class GeneIdentifier(CustomBaseModel):
    id: str = Field(title="Ensembl ID", description="Ensembl gene identifier")
    gene_symbol: Optional[str] = Field(
        default=None,
        title="Gene Symbol",
        description="official gene symbol",
        serialization_alias="symbol",
    )

    def __str__(self):
        return self.id
