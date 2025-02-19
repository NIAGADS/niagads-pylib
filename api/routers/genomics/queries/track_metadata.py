
from typing import List

from api.models.query_defintion import QueryDefinition

from api.routers.genomics.models.feature_score import QTL, VariantPValueScore
from api.routers.genomics.models.genomics_track import GenomicsTrack

# FIXME: this complex query will go away once metadata is loaded as JSON documents

_TRACK_METADATA_QUERY_SQL="SELECT * FROM NIAGADS.TrackMetadata"

TrackMetadataQuery = QueryDefinition(
    query=_TRACK_METADATA_QUERY_SQL,
    rowModel=GenomicsTrack,
    useIdSelectWrapper=True
)

