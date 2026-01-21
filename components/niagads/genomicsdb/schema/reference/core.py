# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002

from niagads.genomicsdb.schema.reference.base import ReferenceTableBase
from niagads.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.genomicsdb.schema.reference.externaldb import ExternalDatabase
