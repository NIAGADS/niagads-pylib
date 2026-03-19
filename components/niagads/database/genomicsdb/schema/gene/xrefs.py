from niagads.enums.core import CaseInsensitiveEnum
from niagads.database.genomicsdb.schema.gene.base import GeneTableBase
from niagads.database.genomicsdb.schema.gene.helpers import gene_fk_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin


class GeneXRefType(CaseInsensitiveEnum):
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
    __table_args__ = (
        *ExternalDatabaseMixin.__table_args__,
        GeneTableBase.__table_args__,
    )
    _stable_id = None
    xref_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gene_id: Mapped[int] = gene_fk_column()
    cross_references: Mapped[dict] = mapped_column(JSONB, nullable=True)
