from fastapi import APIRouter

router = APIRouter(prefix="/record/gene", tags=["Records", "Genes"])


@router.get(
    "/{gene}",
    summary="get-gene-record",
    description="Retrieve the canonical GenomicsDB gene record by gene identifier.",
)
async def get_gene_record(gene: str):
    pass


@router.get(
    "/{gene}/pathways",
    summary="get-gene-pathways",
    description="Retrieve pathway membership for a gene.",
)
async def get_gene_pathways(gene: str):
    pass


@router.get(
    "/{gene}/gene-sets",
    summary="get-gene-sets",
    description="Retrieve curated gene-set membership for a gene.",
)
async def get_gene_sets(gene: str):
    pass


@router.get(
    "/{gene}/function",
    summary="get-gene-function",
    description="Retrieve functional annotations for a gene.",
)
async def get_gene_function(gene: str):
    pass


@router.get(
    "/{gene}/associations",
    summary="get-gene-associations",
    description="Retrieve genetic associations related to a gene.",
)
async def get_gene_associations(gene: str):
    pass


@router.get(
    "/{gene}/link-outs",
    summary="get-gene-link-outs",
    description="Retrieve external resource links for a gene.",
)
async def get_gene_link_outs(gene: str):
    pass
