from typing import Dict, List, Optional, Union

from niagads.api.common.models.domain.base import ORMCompatibleRecord
from niagads.api.common.models.domain.mixins import DynamicMixin, ORMCompatabileMixin
from niagads.common.gene.models.annotation import (
    GOAssociation,
    PathwayMembership,
)
from niagads.common.gene.models.record import GeneRecord
from niagads.common.genomic.regions.models import GenomicRegion

from pydantic import Field


class GeneDescriptor(GeneRecord, ORMCompatabileMixin):
    id: str = Field(title="Ensembl ID", description="Ensembl gene identifier")
    gene_symbol: Optional[str] = Field(
        default=None,
        title="Gene Symbol",
        description="official gene symbol",
        serialization_alias="symbol",
    )
    location: Optional[GenomicRegion] = Field(
        default=None,
        title="Location",
        description="genomic location delimiting the footprint (span) of the gene",
    )

    def __str__(self):
        return self.id


class Gene(GeneDescriptor):
    gene_type: Optional[str] = Field(default=None, serialization_alias="type")
    gene_name: Optional[str] = Field(default=None, serialization_alias="name")
    synonyms: Optional[List[str]] = Field(
        default=None, title="Aliases", descriptions="gene symbol synonyms or aliases"
    )
    cytogenic_location: Optional[str] = Field(
        default=None,
        title="Cytogenic Location",
        description="mapping the gene to a band of the chromosome",
    )

    def __str__(self):
        return self.to_info_string()


class AnnotatedGene(Gene):
    nomenclature: Optional[Dict[str, Union[str, int]]] = None
    go_annotation: Optional[List[GOAssociation]] = None
    pathway_membership: Optional[List[PathwayMembership]] = None


# want to see if this can work for pathways, go etc
class GeneAnnotation(ORMCompatibleRecord, DynamicMixin): ...
