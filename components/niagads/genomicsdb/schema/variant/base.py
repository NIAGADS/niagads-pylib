"""
Base class for the `Variant` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.schema.base.factory import DeclarativeModelBaseFactory

VariantSchemaBase = DeclarativeModelBaseFactory.create(
    schema="variant", incl_housekeeping=True
)

# TODO: when we make this table: need metaseq_id + variant_id b/c there will be cases when the metaseq_id is long that we need an abbreviated variant_id
