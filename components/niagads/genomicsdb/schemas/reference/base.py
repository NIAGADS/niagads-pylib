"""
Base class for the `Core` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.database.core import DeclarativeModelBaseFactory

ReferenceSchemaBase = DeclarativeModelBaseFactory.create(
    schema="reference", incl_housekeeping=True
)
