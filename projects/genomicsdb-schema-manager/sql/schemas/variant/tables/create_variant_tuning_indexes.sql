-- TUNING INDEXES BUILT AFTER BIG LOAD, SEE create_variant_tuning_indexes.sql FILE
-- EMBEDDING INDEXES BUILD AFTER BIG LOAD, don't forget to make them partial (i.e., embedding not null)

SET maintenance_work_mem="16GB";
SET max_parallel_maintenance_workers TO 3;
SET max_parallel_workers TO 3;

CREATE INDEX IX_VARIANT_VARIANT__EMBEDDING_RUN_ID ON Variant.Variant(EMBEDDING_RUN_ID) WHERE EMBEDDING_RUN_ID IS NOT NULL;
CREATE INDEX IX_VARIANT_VARIANT__RUN_ID ON Variant.Variant(RUN_ID);
CREATE INDEX IX_VARIANT_VARIANT__EXTERNAL_DATABASE_ID ON Variant.Variant(EXTERNAL_DATABASE_ID);
/* TODO: gist index on span for SVs, but probably need to do same way did bin_index index
CREATE INDEX ix_variant_variant__span_gist
ON Variant.Variant
USING GIST (span);
*/