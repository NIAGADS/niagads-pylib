-- TUNING INDEXES BUILT AFTER BIG LOAD, SEE create_variant_tuning_indexes.sql FILE
-- EMBEDDING INDEXES BUILD AFTER BIG LOAD, don't forget to make them partial (i.e., embedding not null)

CREATE INDEX IX_VARIANT_VARIANT__EMBEDDING_RUN_ID ON Variant.Variant(EMBEDDING_RUN_ID) WHERE EMBEDDING_RUN_ID IS NOT NULL;

/* TODO: gist index on span for SVs, but probably need to do same way did bin_index index
CREATE INDEX ix_variant_variant__span_gist
ON Variant.Variant
USING GIST (span);
*/