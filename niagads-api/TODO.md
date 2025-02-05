# TODO

## FILER Collections

* create database structure
* python script to populate track links from CSV?

```sql
CREATE TABLE ServerApplication.FILERCollection (
    collection_id SERIAL PRIMARY KEY,
    name CHARACTER VARYING(100) NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE ServerApplication.FILERCollectionTrackLink (
    collection_track_link_id SERIAL PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES ServerApplication.FILERCollection(collection_id),
    track_id CHARACTER VARYING(50) NOT NULL REFERENCES ServerApplication.FILERTrack(track_id)
);

GRANT SELECT ON ServerApplication.FILERCollection TO server_app;
GRANT SELECT ON ServerApplication.FILERCollectionTrackLink TO server_app;

INSERT INTO ServerApplication.FILERCollection (name, description)
SELECT 
'xQTL-Project',
'quantitative trait loci (QTL) are genetic regions that influence phenotypic variation of a molecular (transcriptomic, proteomic, lipidomic among others) trait. The xQTL project is a collaborative effort across the FunGen-AD, the Accelerating Medicines Partnership Alzheimer’s Disease (AMP AD), the NIH Center for Alzheimer’s and Related Dementias (CARD), and the ADSP.'
;
SELECT * FROM ServerApplication.FILERCollection;

INSERT INTO ServerApplication.FILERCollectionTrackLink (collection_id, track_id)
SELECT c.collection_id,
t.track_id
FROM ServerApplication.FilerTrack t, (SELECT collection_id FROM ServerApplication.FILERCollection WHERE name = 'xQTL-Project') c
WHERE t.name like '%significant%' and t.feature_type ilike '%qtl%' and t.name not like '%nomin%' AND t.name LIKE '%NG00102%';
```
