"""
SQLAlchemy ORM table definitions for tables supporting RAG document queries.
"""

from niagads.genomicsdb.schema.base import DeclarativeTableBase
from sqlalchemy import MetaData


class RAGDocSchemaBase(DeclarativeTableBase):
    metadata = MetaData(schema="ragdoc")
    stable_id = None
