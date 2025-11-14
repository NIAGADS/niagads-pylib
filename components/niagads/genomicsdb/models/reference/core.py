# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002

from niagads.genomicsdb.models.reference.base import ReferenceSchemaBase
from niagads.genomicsdb.models.reference.interval_bin import IntervalBin
from niagads.genomicsdb.models.reference.externaldb import ExternalDatabase
