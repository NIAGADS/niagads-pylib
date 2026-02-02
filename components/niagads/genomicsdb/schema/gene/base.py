"""
Base classes for SQLAlchemy ORM models in the GenomicsDB "Gene" schema.
"""

from niagads.genomicsdb.schema.mixins import GenomicsDBMVMixin, GenomicsDBTableMixin
from niagads.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import MetaData, func
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.hybrid import hybrid_property


@SchemaRegistry.register()
class GeneSchemaBase(DeclarativeBase):
    metadata = MetaData(schema="gene")


class GeneTableBase(GeneSchemaBase, GenomicsDBTableMixin, ExternalDatabaseMixin):
    __abstract__ = True
    _stable_id = "source_id"

    @hybrid_property
    def ensembl_id(self):
        return self.source_id

    @ensembl_id.expression
    def ensembl_id(cls):
        return cls.source_id


class GeneMaterializedViewBase(GeneSchemaBase, GenomicsDBMVMixin):
    __abstract__ = True
    _document_primary_key = "gene_id"
    _stable_id = "ensembl_id"
