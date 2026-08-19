SET maintenance_work_mem="16GB";
SET max_parallel_maintenance_workers TO 3;
SET max_parallel_workers TO 3;


-- Create the parent partitioned index metadata only.
-- Child indexes must already exist on each partition.
CREATE INDEX IF NOT EXISTS ix_variant_variant__bin_index
ON ONLY variant.variant USING GIST (bin_index);

-- Attach each existing child index to the parent index.
ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr1__bin_index;


ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr2__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr3__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr4__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr5__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr6__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr7__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr8__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr9__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr10__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr11__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr12__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr13__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr14__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr15__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr16__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr17__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr18__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr19__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr20__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr21__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chr22__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chrx__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chry__bin_index;

ALTER INDEX variant.ix_variant_variant__bin_index
ATTACH PARTITION variant.ix_variant_chrm__bin_index;