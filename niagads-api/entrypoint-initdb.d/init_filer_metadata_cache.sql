\connect apistaticdb; 

DROP TABLE IF EXISTS ServerApplication.FILERTrack CASCADE;

CREATE TABLE ServerApplication.FILERTrack (
        track_id CHARACTER VARYING(50) PRIMARY KEY NOT NULL,
        name     CHARACTER VARYING(250) NOT NULL,
        description TEXT,
        genome_build CHARACTER VARYING(50) CHECK (genome_build IN ('GRCh38', 'GRCh37', 'T2T', 'Pangenome')),
        feature_type CHARACTER VARYING(100),

        download_only BOOLEAN,
        
        -- biosample
        biosample_characteristics JSONB,

        -- experimental design 
        biological_replicates CHARACTER VARYING(100),
        technical_replicates CHARACTER VARYING(100),
        antibody_target CHARACTER VARYING(100),
        assay CHARACTER VARYING(100),
        analysis TEXT,
        classification TEXT,
        data_category CHARACTER VARYING(150),
        output_type CHARACTER VARYING(150),
        is_lifted BOOLEAN,
        experiment_info TEXT,
        study_id CHARACTER VARYING(150),
        study_name CHARACTER VARYING(250),
        dataset_id CHARACTER VARYING(150),
        pubmed_id CHARACTER VARYING(25),
        sample_group CHARACTER VARYING(250),
        
        --provenance
        data_source CHARACTER VARYING(50),
        data_source_version CHARACTER VARYING(50),
        download_url CHARACTER VARYING(500),
        download_date DATE,
        release_date DATE,
        filer_release_date DATE,
        experiment_id CHARACTER VARYING(50),
        project CHARACTER VARYING(100),
        
        --FILER file properties
        file_name CHARACTER VARYING(500),
        url CHARACTER VARYING(500),
        md5sum CHARACTER VARYING(250),
        raw_file_url CHARACTER VARYING(500),
        raw_file_md5sum CHARACTER VARYING(250),
        bp_covered BIGINT,
        number_of_intervals BIGINT,
        file_size BIGINT,
        file_format CHARACTER VARYING(25),
        file_schema CHARACTER VARYING(50),
        searchable_text TEXT  
);

CREATE INDEX FTM_IND01 ON ServerApplication.FILERTrack(name, track_id);
CREATE INDEX FTM_IND02 ON ServerApplication.FILERTrack (genome_build, track_id);
CREATE INDEX FTM_IND03 ON ServerApplication.FILERTrack (feature_type, track_id);
CREATE INDEX FTM_IND04 ON ServerApplication.FILERTrack (assay, track_id);
CREATE INDEX FTM_IND05 ON ServerApplication.FILERTrack (data_category, track_id);
CREATE INDEX FTM_IND06 ON ServerApplication.FILERTrack (antibody_target, track_id);
CREATE INDEX FTM_IND07 ON ServerApplication.FILERTrack (data_source, track_id);
CREATE INDEX FTM_IND08 ON ServerApplication.FILERTrack (project, track_id);

DROP TABLE IF EXISTS ServerApplication.FILERCollection CASCADE;

CREATE TABLE ServerApplication.FILERCollection (
    collection_id SERIAL PRIMARY KEY,
    name CHARACTER VARYING(100) NOT NULL,
    description TEXT NOT NULL
);

DROP TABLE IF EXISTS ServerApplication.FILERCollectionTrackLink CASCADE;

CREATE TABLE ServerApplication.FILERCollectionTrackLink (
    collection_track_link_id SERIAL PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES ServerApplication.FILERCollection(collection_id),
    track_id CHARACTER VARYING(50) NOT NULL REFERENCES ServerApplication.FILERTrack(track_id)
);

CREATE INDEX FCTL_IND01 ON ServerApplication.FILERCollectionTrackLink(collection_id);
CREATE INDEX FCTL_IND02 ON ServerApplication.FILERCollectionTrackLink(track_id);

GRANT SELECT ON ServerApplication.FILERCollection TO server_app;
GRANT SELECT ON ServerApplication.FILERCollectionTrackLink TO server_app;




   
-- Grants (may need to do them again here)

GRANT SELECT ON ALL TABLES IN SCHEMA ServerApplication TO server_app;