# TODO

## FILER Collections

* create database structure
* python script to populate track links from CSV?

```sql
INSERT INTO ServerApplication.FILERCollection (name, description)
SELECT 
'FunGen-xQTL',
'quantitative trait loci (QTL) are genetic regions that influence phenotypic variation of a molecular (transcriptomic, proteomic, lipidomic among others) trait. The FunGen-xQTL project is a collaborative effort across the FunGen-AD, the Accelerating Medicines Partnership Alzheimer’s Disease (AMP AD), the NIH Center for Alzheimer’s and Related Dementias (CARD), and the ADSP.'
;
SELECT * FROM ServerApplication.FILERCollection;



INSERT INTO ServerApplication.FILERCollection (name, description)
SELECT 
'AD-related', 
'This collection groups functional genomics data tracks in brain, immune, or blood cells (tissues) from primary cells (tissues) or in-vitro differentiated cells.  These include data tracks from the ENCODE RUSH AD project and GTEx QTLs.';


UPDATE FILERTrack 
SET download_only = TRUE
WHERE data_category = 'QTL'
AND output_type LIKE '%all%' OR output_type LIKE '%nominal%';

UPDATE FILERTrack
SET download_only = TRUE
WHERE file_schema = 'broadPeak';

INSERT INTO ServerApplication.FILERCollectionTrackLink (collection_id, track_id)
SELECT DISTINCT c.collection_id, t.track_id
FROM 
(SELECT collection_id FROM ServerApplication.FILERCollection WHERE name = 'AD-related') c,
(SELECT track_id FROM FILERTrack WHERE biosample_characteristics->>'tissue_category' ~ 'Brain|Immune|Blood$'
AND biosample_characteristics->>'biosample_type' ~ 'primary cell|tissue|in vitro'
AND download_only IS NULL ORDER BY data_source,track_id) t;

```
