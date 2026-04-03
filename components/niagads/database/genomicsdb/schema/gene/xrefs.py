from enum import auto
from typing import Optional
from niagads.database.genomicsdb.schema.reference.helpers import ontology_term_fk_column
from niagads.database.helpers import enum_column, enum_constraint
from niagads.enums.core import CaseInsensitiveEnum
from niagads.database.genomicsdb.schema.gene.base import GeneTableBase
from niagads.database.genomicsdb.schema.gene.helpers import gene_fk_column
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from niagads.database.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin


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


class GeneXRefCategory(CaseInsensitiveEnum):
    IDENTIFIER = auto()
    LOCUS = auto()
    PUBLICATION = auto()
    RESOURCE_LINK = auto()
    CLASSIFICATION = auto()
    GROUP_MEMBERSHIP = auto()
    ORTHOLOG = auto()


# NOTE: not using the ExternalDatabaseMixin because there is no source_id
class GeneXRef(GeneTableBase):
    __tablename__ = "xref"
    __table_args__ = (
        enum_constraint("xref_category", GeneXRefCategory),
        GeneTableBase.__table_args__,
    )
    _stable_id = None
    xref_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    external_database_id: Mapped[int] = mapped_column(
        ForeignKey("reference.externaldatabase.external_database_id"),
        nullable=False,
        index=True,
    )
    gene_id: Mapped[int] = gene_fk_column()
    xref_category: Mapped[GeneXRefCategory] = enum_column(
        GeneXRefCategory, index=True, nullable=False
    )
    xref_label: Mapped[Optional[str]] = mapped_column(
        String(50), index=True, nullable=True
    )
    xref_value: Mapped[Optional[str]] = mapped_column(
        String(250), index=True, nullable=True
    )

    ontology_term_id: Mapped[Optional[int]] = ontology_term_fk_column(
        nullable=True, index=True
    )
    cross_references: Mapped[Optional[dict]] = mapped_column(
        JSONB(none_as_null=True), nullable=True
    )
