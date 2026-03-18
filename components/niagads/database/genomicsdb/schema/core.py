# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002
# it also necessary to use GenomicsDBSchemaBase registry-based class methods (must import from here)

from niagads.database.genomicsdb.schema.base import GenomicsDBSchemaBase

# Admin Schema
from niagads.database.genomicsdb.schema.admin.etl import ETLRun
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog, SchemaCatalog

# Dataset Schema

from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.dataset.collection import (
    Collection,
    TrackCollectionLink,
)

# Gene Schema
from niagads.database.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.database.genomicsdb.schema.gene.documents import Gene
from niagads.database.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.database.genomicsdb.schema.gene.structure import (
    GeneModel,
    ExonModel,
    TranscriptModel,
)
from niagads.database.genomicsdb.schema.gene.xrefs import GeneXRef

# RagDoc Schema

from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)

# Reference Schema

from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.database.genomicsdb.schema.reference.pathway import Pathway

# Variant Schema
