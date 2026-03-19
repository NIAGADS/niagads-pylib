# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002

from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.database.genomicsdb.schema.reference.pathway import Pathway
