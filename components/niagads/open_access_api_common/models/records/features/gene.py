from typing import Dict, List, Optional, Union

from niagads.open_access_api_common.models.records.core import RowModel
from niagads.open_access_api_common.models.records.features.genomic import GenomicRegion
from niagads.open_access_api_common.models.response.core import PagedResponseModel


class GeneFeature(RowModel):
    ensembl_id: str
    gene_symbol: Optional[str] = None


class Gene(GeneFeature):
    type: str
    name: str
    location: GenomicRegion
    cytogenic_location: Optional[str] = None
    # summary: Optional[str] = None


class AnnotatedGene(Gene):
    mappings: Dict[str, Union[str, int]]
    # rifs: Optional[dict] = None
    function: Optional[dict] = None
    pathways: Optional[dict] = None
    # relationships: Optional[dict] = None


class GeneSummaryResponse(PagedResponseModel):
    data: List[Gene]


class AnnotatedGeneResponse(PagedResponseModel):
    data: List[AnnotatedGene]
