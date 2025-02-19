
from typing import List

from api.models.query_defintion import QueryDefinition

from api.routers.genomics.models.feature_score import QTL, VariantPValueScore
from api.routers.genomics.models.genomics_track import GenomicsTrack

# FIXME: this complex query will go away once metadata is loaded as JSON documents

_TRACK_METADATA_QUERY_SQL="""
WITH Covariates AS (
SELECT protocol_app_node_id, replace(characteristic, 'adjusted for ', '') AS covariates
FROM NIAGADS.ProtocolAppNodeCharacteristic
WHERE characteristic_type = 'covariate_list'),

Phenotypes AS (
SELECT protocol_app_node_id, 
jsonb_object_agg(
CASE WHEN characteristic_type = 'diagnosis' THEN 'disease' 
WHEN characteristic_type LIKE 'APOE%' THEN 'genotype' 
ELSE characteristic_type END,
CASE WHEN characteristic LIKE '%Alzhe%' THEN 'Alzheimer''s disease' ELSE characteristic END) AS phenotypes
FROM NIAGADS.ProtocolAppNodeCharacteristic
WHERE characteristic_type NOT IN ('full_list', 'phenotype_list', 'tissue', 'covariate_list', 'covariate specification')
AND characteristic NOT LIKE 'autopsy%'
GROUP BY protocol_app_node_id),

Metadata AS (
SELECT pan.protocol_app_node_id, ta.track AS track_id, ta.track AS id, ta.name, 
'GRCh38'::text AS genome_build,
CASE WHEN ta.subcategory = 'QTL' THEN pan.track_summary->>'feature_type' ELSE 'variant' END AS feature_type,
CASE WHEN ta.track LIKE '%_GRCh38_%' THEN TRUE ELSE FALSE END AS is_lifted,
ta.subcategory AS data_category,
pan.uri AS url,
jsonb_build_object(
'consortia', pan.track_summary->'consortium',
'accession', da.accession, 'pubmed_id', 
split_part(da.attribution, '|', 2), 
'attribution', split_part(da.attribution, '|', 1)) AS provenance,
pan.track_summary->>'experimental_design' AS experimental_design,
pan.track_summary->>'biosample_characteristics' AS biosample_characteristics,
CASE WHEN pan.track_summary->>'cohorts' NOT LIKE '%[%' --some are saved as concatenated and some as arrays
THEN to_jsonb(string_to_array(pan.track_summary->>'cohorts', ',')) 
ELSE pan.track_summary->'cohorts' END as cohorts,
jsonb_build_array(jsonb_build_object('group', 'Cases', 'num_samples', pan.track_summary->'ncase'),
jsonb_build_object('group', 'Control', 'num_samples', pan.track_summary->'ncontrol')) AS study_groups,
ta.description
FROM NIAGADS.TrackAttributes ta,
NIAGADS.DatasetAttributes da,
Study.ProtocolAppNode pan
WHERE ta.dataset_accession = da.accession
AND pan.protocol_app_node_id = ta.protocol_app_node_id) -- 79
SELECT DISTINCT m.*, c.covariates, p.phenotypes
FROM Metadata m 
LEFT OUTER JOIN Phenotypes p ON p.protocol_app_node_id = m.protocol_app_node_id
LEFT OUTER JOIN Covariates c ON c.protocol_app_node_id = m.protocol_app_node_id
"""

TrackMetadataQuery = QueryDefinition(
    query=_TRACK_METADATA_QUERY_SQL,
    rowModel=GenomicsTrack,
    useIdSelectWrapper=True
)

