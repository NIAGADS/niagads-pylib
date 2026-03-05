# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002
# it also necessary to use GenomicsDBSchemaBase registry-based class methods (must import from here)

from niagads.genomicsdb.schema.base import GenomicsDBSchemaBase

# Admin Schema
from niagads.genomicsdb.schema.admin.etl import ETLRun
from niagads.genomicsdb.schema.admin.catalog import TableCatalog, SchemaCatalog

# Dataset Schema

from niagads.genomicsdb.schema.dataset.track import Track
from niagads.genomicsdb.schema.dataset.collection import (
    Collection,
    TrackCollectionLink,
)

# Gene Schema
from niagads.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.genomicsdb.schema.gene.documents import Gene
from niagads.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.genomicsdb.schema.gene.structure import (
    GeneModel,
    ExonModel,
    TranscriptModel,
)
from niagads.genomicsdb.schema.gene.xrefs import GeneXRef

# RagDoc Schema

from niagads.genomicsdb.schema.ragdoc.documents import (
    ChunkEmbedding,
    ChunkMetadata,
)

# Reference Schema

from niagads.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.genomicsdb.schema.reference.pathway import Pathway

# Variant Schema
