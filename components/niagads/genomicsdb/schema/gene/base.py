"""
Base classes for SQLAlchemy ORM models in the GenomicsDB "Gene" schema.
"""

from niagads.genomicsdb.schema.mixins import GenomicsDBMVMixin, GenomicsDBTableMixin
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


@SchemaRegistry.register()
class GeneSchemaBase(DeclarativeBase):
    metadata = MetaData(schema="dataset")


class GeneTableBase(GeneSchemaBase, GenomicsDBTableMixin):
    stable_id = "source_id"


class GeneMaterializedViewBase(GeneSchemaBase, GenomicsDBMVMixin):
    document_primary_key = "gene_id"
    stable_id = "ensembl_id"
