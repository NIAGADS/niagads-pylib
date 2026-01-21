# schema_helpers.py

from enum import Enum

# note the schema base is imported from `core`, which contains both the base and the models
# not `base`, which just defines the base; this ensures all tables are generated
# see https://stackoverflow.com/a/77767002
from niagads.genomicsdb.schema.admin.core import AdminSchema
from niagads.genomicsdb.schema.dataset.core import DatasetSchemaBase
from niagads.genomicsdb.schema.gene.core import GeneSchemaBase
from niagads.genomicsdb.schema.ragdoc.base import RAGDocSchemaBase
from niagads.genomicsdb.schema.reference.core import ReferenceTableBase
from niagads.genomicsdb.schema.variant.core import VariantSchemaBase
