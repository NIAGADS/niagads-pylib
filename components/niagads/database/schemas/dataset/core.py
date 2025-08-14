"""Core dataset schema module.

This module sets up imports for Alembic to recognize all models associated with the dataset schema.
"""

# this set up is necessary for Alembic to import all the models associated with the metadata schema
# see https://stackoverflow.com/a/77767002

from niagads.database.schemas.dataset.base import DatasetSchemaBase
from niagads.database.schemas.dataset.track import Track
from niagads.database.schemas.dataset.collection import Collection, TrackCollection
