# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002
#  FIXME: can I just use __init__.py?

from niagads.genomicsdb.schema.gene.base import GeneSchemaBase
from niagads.genomicsdb.schema.gene.documents import Gene
from niagads.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.genomicsdb.schema.gene.structure import (
    GeneModel,
    ExonModel,
    TranscriptModel,
)
from niagads.genomicsdb.schema.gene.xrefs import GeneXRef
