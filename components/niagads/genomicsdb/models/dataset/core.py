# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002

from niagads.genomicsdb.models.dataset.base import DatasetSchemaBase
from niagads.genomicsdb.models.dataset.track import Track
from niagads.genomicsdb.models.dataset.collection import (
    Collection,
    TrackCollection,
)
