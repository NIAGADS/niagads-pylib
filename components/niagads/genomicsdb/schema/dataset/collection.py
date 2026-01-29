"""core defines the `Collection` and link between tracks and collections (metadata) database models"""

from niagads.database.mixins import CollectionMixin, TrackCollectionMixin
from niagads.genomicsdb.schema.dataset.base import DatasetSchemaBase
from niagads.genomicsdb.schema.mixins import IdAliasMixin


# this just adds housekeeping, etc to these schemas
class Collection(DatasetSchemaBase, CollectionMixin, IdAliasMixin):
    stable_id = "collection_key"


class TrackCollectionLink(DatasetSchemaBase, TrackCollectionMixin):
    stable_id = None
