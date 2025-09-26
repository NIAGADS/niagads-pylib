"""
Base class for the `Gene` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.models.base import DeclarativeModelBaseFactory

GeneSchemaBase = DeclarativeModelBaseFactory.create(
    schema="gene", incl_housekeeping=True
)

GeneMaterializedViewBase = DeclarativeModelBaseFactory.create(
    schema="gene", incl_housekeeping=False, enable_query_mixin=False
)
