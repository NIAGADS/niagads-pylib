# Bin-Aware SeqRepo Cache Plan

## Goal

Speed up GA4GH VRS validation and normalization by reducing repeated SeqRepo
sequence fetches. The cache belongs in the GA4GH annotator path, not in a
specific ETL plugin.

## Approach

- Wrap the existing SeqRepo data proxy with a bin-aware caching proxy.
- Pass the existing in-memory `bin_index_reference` into `PrimaryKeyGenerator`,
  then into `GA4GHVRSService`.
- Let GA4GH continue calling the data proxy normally.
- Intercept only sequence retrieval behavior:
  - `get_sequence(...)`
  - `validate_ref_seq(...)`
- Keep GA4GH translator, normalization, and VRS ID generation unchanged.

## Cache Design

- Cache key: `(refget_accession, bin_index)`.
- Cache value: `(bin_start, bin_end, sequence)`.
- Use the smallest existing bin that fully contains the requested sequence
  interval.
- If the smallest bin does not contain the request, use an enclosing parent bin.
- Only cache bins up to `1_000_000` bp.
- If no acceptable bin is found, fall back to the direct SeqRepo request.
- Keep a small per-service LRU cache, initially `8` bins.

## Coordinate Handling

- GA4GH sequence requests are zero-based half-open: `[start, end)`.
- Existing interval bins are one-based inclusive.
- Convert before resolving bins:
  - `one_based_start = start + 1`
  - `one_based_end = max(one_based_start, end)`
- Cached SeqRepo fetch uses zero-based half-open bin coordinates:
  - `bin_fetch_start = bin_start - 1`
  - `bin_fetch_end = bin_end`

## Integration Points

- `BaseFeatureLoaderPlugin` exposes `bin_index_reference` as a read-only property.
- `BaseVCFLoader.on_run_start(...)` passes the bin reference into
  `PrimaryKeyGenerator`.
- `PrimaryKeyGenerator` passes it into `GA4GHVRSService`.
- `GA4GHVRSService` wraps the raw SeqRepo data proxy with
  `BinCachedSeqRepoDataProxy`.

## Important Constraints

- Do not rewrite GA4GH normalization.
- Do not cache whole chromosomes.
- Do not make this dbSNP-specific.
- Preserve existing fallback behavior when no bin map is available.
- Keep `get_refget_accession()` caching unchanged.

## Verification

- Compile touched files.
- Smoke test that two same-bin `get_sequence(...)` requests result in one
  underlying SeqRepo sequence fetch.
- Later, profile dbSNP transform to confirm SeqRepo sequence calls drop during
  validation/normalization.
