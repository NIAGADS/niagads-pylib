# TODO

## FILER Collections & DB patches after load

* create database structure
* python script to populate track links from CSV?

```sql
-- QTLs

UPDATE FILERTrack 
SET download_only = TRUE
WHERE data_category = 'QTL'
AND output_type LIKE '% all %' OR output_type LIKE '%nominally%';


INSERT INTO ServerApplication.FILERCollection (name, description, tracks_are_sharded)
SELECT 
'ADSP-FunGen-xQTL',
'quantitative trait loci (QTL) are genetic regions that influence phenotypic variation of a molecular trait(transcriptomic, proteomic, lipidomic among others). The FunGen-xQTL project is a collaborative effort across the FunGen-AD, the Accelerating Medicines Partnership Alzheimer’s Disease (AMP AD), the NIH Center for Alzheimer’s and Related Dementias (CARD), and the ADSP.',
TRUE
;

INSERT INTO FILERCollectionTrackLink(collection_id, track_id)
SELECT c.collection_id, t.track_id 
FROM (SELECT track_id  FROM FILERTrack WHERE NAME LIKE 'FunGen xQTL%' AND is_shard AND track_id = shard_parent_track_id) t,
(SELECT collection_id FROM FILERCollection WHERE NAME = 'ADSP-FunGen-xQTL') c;

```

```sql

UPDATE FILERTrack
SET download_only = TRUE
WHERE file_schema = 'broadPeak';


INSERT INTO ServerApplication.FILERCollection (name, description)
SELECT 
'AD-related', 
'This collection groups functional genomics data tracks in brain, immune, or blood cells (tissues) from primary cells (tissues) or in-vitro differentiated cells.  These include data tracks from the ENCODE RUSH AD project and GTEx QTLs.';


INSERT INTO ServerApplication.FILERCollectionTrackLink (collection_id, track_id)
SELECT DISTINCT c.collection_id, t.track_id
FROM 
(SELECT collection_id FROM ServerApplication.FILERCollection WHERE name = 'AD-related') c,
(SELECT track_id FROM FILERTrack WHERE biosample_characteristics->>'tissue_category' ~ 'Brain|Immune|Blood$'
AND biosample_characteristics->>'biosample_type' ~ 'primary cell|tissue|in vitro'
AND download_only IS NULL ORDER BY data_source,track_id) t;

```
