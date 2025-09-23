"""
Base class for the `Variant` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.database.core import DeclarativeModelBaseFactory

VariantSchemaBase = DeclarativeModelBaseFactory.create(
    schema="variant", incl_housekeeping=True
)
