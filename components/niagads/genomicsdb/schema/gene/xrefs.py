from niagads.enums.core import CaseInsensitiveEnum
from niagads.genomicsdb.schema.gene.base import GeneTableBase, gene_fk_column
from niagads.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column


class GeneIdentifierType(CaseInsensitiveEnum):
    ENSEMBL = "ensembl_id"
    ENTREZ = "entrez_id"
    NCBI = "entrez_id"
    SYMBOL = "gene_symbol"
    HGNC = "hgnc_id"
    UNIPROT = "uniprot_id"
    OMIM = "omim_id"
    UCSC = "ucsc_id"
    REFSEQ = "refseq_id"
    # TODO: orthologs?


class GeneXRef(GeneTableBase, ExternalDatabaseMixin):
    __tablename__ = "xref"
    stable_id = None
    gene_id: Mapped[int] = gene_fk_column()
    cross_references: Mapped[dict] = mapped_column(JSONB, nullable=True)
