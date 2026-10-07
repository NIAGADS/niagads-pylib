# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002
# it also necessary to use GenomicsDBSchemaBase registry-based class methods (must import from here)

from niagads.database.genomicsdb.schema.admin.catalog import SchemaCatalog, TableCatalog

# Admin Schema
from niagads.database.genomicsdb.schema.admin.etl import ETLRun
from niagads.database.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.database.genomicsdb.schema.dataset.collection import (
    Collection,
    TrackCollectionLink,
)
from niagads.database.genomicsdb.schema.dataset.track import Track

# Gene Schema
from niagads.database.genomicsdb.schema.gene.annotation import PathwayMembership
from niagads.database.genomicsdb.schema.gene.documents import Gene
from niagads.database.genomicsdb.schema.gene.structure import (
    ExonModel,
    GeneModel,
    TranscriptModel,
)
from niagads.database.genomicsdb.schema.gene.xrefs import GeneXRef
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.database.genomicsdb.schema.reference.interval_bin import IntervalBin
from niagads.database.genomicsdb.schema.reference.ontology import OntologyTerm
from niagads.database.genomicsdb.schema.reference.pathway import Pathway

# Dataset Schema


# RagDoc Schema


# Reference Schema


# Variant Schema
