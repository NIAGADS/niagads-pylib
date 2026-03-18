"""
SQLAlchemy ORM table definitions for tables supporting RAG document queries.
"""

from niagads.database.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.database.genomicsdb.schema.mixins import GenomicsDBTableMixin


class RAGDocTableBase(GenomicsDBSchemaBase, GenomicsDBTableMixin):
    __abstract__ = True
    _stable_id = None
    _schema = "ragdoc"

    __table_args__ = {"schema": _schema}
