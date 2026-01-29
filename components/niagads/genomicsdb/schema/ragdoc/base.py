"""
SQLAlchemy ORM table definitions for tables supporting RAG document queries.
"""

from niagads.genomicsdb.schema.mixins import GenomicsDBTableMixin
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


@SchemaRegistry.register()
class RAGDocSchemaBase(DeclarativeBase, GenomicsDBTableMixin):
    metadata = MetaData(schema="ragdoc")
    stable_id = None
