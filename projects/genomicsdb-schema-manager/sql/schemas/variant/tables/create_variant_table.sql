-- table for variants
DROP TABLE IF EXISTS Variant.Variant CASCADE;

/* worth embedding 
functional_consequence
gene_context
regulatory_annotation
clinical_significance
literature_summary
pathway / ontology terms
*/

CREATE TABLE Variant.Variant (
    CHROMOSOME CHARACTER VARYING(10) NOT NULL,
    POSITION INTEGER NOT NULL,
    REF_ALLELE TEXT,
    ALT_ALLELE TEXT,
    LENGTH INTEGER NOT NULL,
    BIN_INDEX LTREE NOT NULL,

    VARIANT_ID CHARACTER VARYING(150) NOT NULL,
    POSITIONAL_ID TEXT, -- nullable because not relevant to SVs
    VARIANT_TYPE CHARACTER VARYING(10) NOT NULL,
    REF_SNP_ID CHARACTER VARYING(25),
    GA4GH_VRS JSONB,
    DISPLAY_ID TEXT NOT NULL, -- just b/c

    IS_ADSP_VARIANT BOOLEAN,
    IS_STRUCTURAL_VARIANT BOOLEAN,

    ADSP_ANNOTATION JSONB, --QC, FAVOR, ADSP MSC

    MOST_SEVERE_CONSEQUNCE JSONB,
    FUNCTIONAL_ANNOTATION JSONB, -- vep, etc
    GWAS_ANNOTATION JSONB,
    ALLELE_FREQUENCY JSONB,
    LINKAGE JSONB,
  
    -- AI generated summary + embeddings
    FUNCTIONAL_ANNOTATION_SUMMARY JSONB, 
    EMBEDDING_HASH BYTEA,
    EMBEDDING VECTOR(384),
    EMBEDDING_MODEL CHARACTER VARYING(250)
    EMBEDDING_DATE DATE,
    EMBEDDING_RUN_ID INTEGER,

    DBSNP_VERSION CHARACTER VARYING (25), -- possibly needed to resolve deprecated ids

    RUN_ID INTEGER NOT NULL,
    CREATION_DATE DATE,
    MODIFICATION_DATE DATE,
    FOREIGN KEY (RUN_ID) REFERENCES Admin.ETLRun(ETL_RUN_ID),
    FOREIGN KEY (EMBEDDING_RUN_ID) REFERENCES Admin.ETLRun(ETL_RUN_ID),
) PARTITION BY LIST (CHROMOSOME);

-- CREATE PARTITIONS
CREATE
OR REPLACE FUNCTION "variant"."create_variant_partitions" () RETURNS integer VOLATILE AS $ body $ DECLARE partition TEXT;

chr TEXT;

BEGIN FOR chr IN
SELECT
    UNNEST(
        string_to_array(
            'chr1 chr2 chr3 chr4 chr5 chr6 chr7 chr8 chr9 chr10 chr11 chr12 chr13 chr14 chr15 chr16 chr17 chr18 chr19 chr20 chr21 chr22 chrX chrY chrM',
            ' '
        )
    ) LOOP partition := 'Variant.VARIANT' || '_' || chr :: text;

IF NOT EXISTS(
    SELECT
        relname
    FROM
        pg_class
    WHERE
        relname = partition
) THEN EXECUTE 'CREATE TABLE ' || partition || ' PARTITION OF Variant.Variant FOR VALUES IN (''' || chr || ''')';

RAISE NOTICE 'A partition has been created %',
partition;

END IF;

END LOOP;

RETURN NULL;

END;

$ body $ LANGUAGE plpgsql;

SELECT
    variant.create_variant_partitions();

--SELECT annotatedvdb.alter_variant_autovacuum(FALSE); -- temp turn off autovacuum
-- TRIGGERS
CREATE
OR REPLACE FUNCTION Variant.set_bin_index() RETURNS TRIGGER LANGUAGE plpgsql AS $ $ BEGIN IF NEW.bin_index IS NULL THEN NEW.bin_index = find_bin_index(
    NEW.chromosome,
    (NEW.display_attributes -> 'location_start') :: int,
    (NEW.display_attributes -> 'location_end') :: int
);

END IF;

RETURN NEW;

END;

$ $;

CREATE TRIGGER variant_set_bin_index
AFTER
INSERT
    ON Variant.Variant EXECUTE PROCEDURE Variant.set_bin_index();

-- INDEXES
CREATE INDEX VARIANT_RECORD_PK_HASH ON AnnotatedVDB.Variant USING HASH(RECORD_PRIMARY_KEY);

CREATE INDEX VARIANT_RS_HASH ON AnnotatedVDB.Variant USING HASH(REF_SNP_ID);

CREATE INDEX VARIANT_METASEQ_LEFT50 ON AnnotatedVDB.Variant(LEFT(METASEQ_ID, 50));

CREATE INDEX VARIANT_BIN_INDEX ON AnnotatedVDB.Variant USING GIST(BIN_INDEX);

CREATE INDEX VARIANT_UNDO_INDEX ON AnnotatedVDB.Variant(ROW_ALGORITHM_ID);

-- brin index not used