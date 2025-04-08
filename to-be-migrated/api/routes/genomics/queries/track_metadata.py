from api.models.query_defintion import QueryDefinition

_TRACK_COLLECTION_METADATA_QUERY="""
    SELECT m.*
    FROM NIAGADS.Collection c, 
    NIAGADS.TrackCollectionLink tcl,
    NIAGADS.TrackMetadata m
    WHERE tcl.collection_id = c.collection_id
    AND tcl.track_id = m.protocol_app_node_id
    AND c.name ILIKE :collection
"""

_TRACK_COLLECTION_QUERY="""
    SELECT c.name, c.description, count(tcl.track_id) AS num_tracks
    FROM NIAGADS.Collection c,
    NIAGADS.TrackCollectionLink tcl
    WHERE c.collection_id = tcl.collection_id
    GROUP BY c.name, c.description
"""


TrackMetadataQuery = QueryDefinition(
    query="SELECT * FROM NIAGADS.TrackMetadata",
    useIdSelectWrapper=True,
    errorOnNull="Track not found in the GenomicsDB"
)

CollectionQuery = QueryDefinition(
    query=_TRACK_COLLECTION_QUERY,
)

CollectionTrackMetadataQuery = QueryDefinition(
    query=_TRACK_COLLECTION_METADATA_QUERY,
    bindParameters=['collection'],
    errorOnNull="Collection not found in the GenomicsDB"
)

