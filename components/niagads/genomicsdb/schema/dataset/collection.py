"""core defines the `Collection` and link between tracks and collections (metadata) database models"""

from niagads.database.mixins import CollectionMixin, TrackCollectionMixin
from niagads.genomicsdb.schema.dataset.base import DatasetSchemaBase


# this just adds housekeeping, etc to these schemas
class Collection(CollectionMixin, DatasetSchemaBase): ...


class TrackCollection(TrackCollectionMixin): ...
