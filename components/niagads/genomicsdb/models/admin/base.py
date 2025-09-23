"""
Base class for the `Core` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.models.base import DeclarativeModelBaseFactory

AdminSchemaBase = DeclarativeModelBaseFactory.create(
    schema="admin", incl_housekeeping=True
)
