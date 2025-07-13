from niagads.open_access_api_common.models.services.query import QueryDefinition


_TRACK_COLLECTION_METADATA_QUERY = """
    SELECT m.*
    FROM Metadata.Collection c, 
    Metadata.TrackCollectionLink tcl,
    Metadata.TrackMetadata m
    WHERE tcl.collection_id = c.collection_id
    AND tcl.track_id = m.protocol_app_node_id
    AND c.name ILIKE :collection
"""

_TRACK_COLLECTION_QUERY = """
    SELECT c.name, c.description, count(tcl.track_id) AS num_tracks
    FROM Metadata.Collection c,
    Metadata.TrackCollectionLink tcl
    WHERE c.collection_id = tcl.collection_id
    GROUP BY c.name, c.description
"""


TrackMetadataQuery = QueryDefinition(
    query="SELECT * FROM Metadata.TrackMetadata",
    use_id_select_wrapper=True,
    errorOnNull="Track not found in the GenomicsDB",
)

CollectionQuery = QueryDefinition(
    query=_TRACK_COLLECTION_QUERY,
)

CollectionTrackMetadataQuery = QueryDefinition(
    query=_TRACK_COLLECTION_METADATA_QUERY,
    bind_parameters=["collection"],
    errorOnNull="Collection not found in the GenomicsDB",
)
