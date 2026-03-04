"""
Base classes for SQLAlchemy ORM models in the GenomicsDB "Gene" schema.
"""

from niagads.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.genomicsdb.schema.mixins import GenomicsDBMVMixin, GenomicsDBTableMixin
from niagads.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from sqlalchemy.ext.hybrid import hybrid_property


class GeneTableBase(GenomicsDBSchemaBase, GenomicsDBTableMixin, ExternalDatabaseMixin):
    __abstract__ = True
    _stable_id = "source_id"
    _schema = "gene"

    __table_args__ = {"schema": _schema}

    @hybrid_property
    def ensembl_id(self):
        return self.source_id

    @ensembl_id.expression
    def ensembl_id(cls):
        return cls.source_id


class GeneMaterializedViewBase(GenomicsDBSchemaBase, GenomicsDBMVMixin):
    __abstract__ = True
    _document_primary_key = "gene_id"
    _stable_id = "ensembl_id"
    _schema = "gene"

    __table_args__ = {"schema": _schema, "info": {"is_view": True}}
