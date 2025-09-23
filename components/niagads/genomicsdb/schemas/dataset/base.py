"""
Base class for the `Dataset` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.database.core import DeclarativeModelBaseFactory

DatasetSchemaBase = DeclarativeModelBaseFactory.create(
    schema="dataset", incl_housekeeping=True
)
