# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002

from niagads.genomicsdb.schema.admin.base import AdminSchemaBase
from niagads.genomicsdb.schema.admin.pipeline import ETLTask
