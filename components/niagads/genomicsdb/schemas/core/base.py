"""
Base class for the `Core` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.database.core import DeclarativeModelBaseFactory

CoreSchemaBase = DeclarativeModelBaseFactory.create(
    schema="core", incl_housekeeping=True
)
