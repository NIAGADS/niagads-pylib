# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002

from niagads.database.models.metadata.base import MetadataSchemaBase
from niagads.database.models.metadata.track import Track
from niagads.database.models.metadata.collection import Collection, TrackCollection
