# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002

from niagads.database.genomicsdb.schemas.reference.base import ReferenceSchemaBase
