SET maintenance_work_mem="16GB";
SET max_parallel_maintenance_workers TO 3;
SET max_parallel_workers TO 3;


-- Create the parent partitioned index metadata only.
-- Child indexes must already exist on each partition.
CREATE INDEX IF NOT EXISTS ix_variant_variant__bin_index
ON ONLY variant.variant USING GIST (bin_index);

-- Attach each existing child index to the parent index.
-- These names must match the indexes created on the partitions.
ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_1__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_2__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_3__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_4__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_5__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_6__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_7__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_8__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_9__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_10__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_11__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_12__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_13__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_14__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_15__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_16__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_17__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_18__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_19__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_20__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_21__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_22__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_x__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_y__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_mt__bin_index;