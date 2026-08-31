# TODOs

## Bugs

### FILER Track Metadata Brief Response

- `data_category` is always null --> was not pulled; added it to the before model validator (untested)
- `is_download_only` should be `True` or `False` not `null` --> added field serializer (untested)

```json
  {
      "id": "NGENCQBEJ2TZUV",
      "name": "ENCODE Thyroid gland (repl. 1) ATAC-seq pseudoreplicated peaks",
      "description": "ENCODE Thyroid gland (repl. 1) ATAC-seq pseudoreplicated peaks (narrowPeak) [Experiment: ENCSR201FIW] [Life stage: Adult]",
      "genome_build": "GRCh38",
      "feature_type": "REGION",
      "is_download_only": null,
      "data_source": "ENCODE",
      "data_category": null,
      "url": "https://tf.lisanwanglab.org/GADB/Annotationtracks/ENCODE/data/ATAC-seq/narrowpeak/hg38/ENCFF413XCR.bed.gz"
    },
```

## Conventions

- query params `_id` ? --> this needs be resolved ASAP/disconnect w/refactor parameter names and expectations in endpoint services

## Refactor Targets

- centralize in MetadataQueryService transformations of Tracks to APIRecords (b/c needed for direct and indirect [e.g., collection] queries) <-- DONE/untested
- messaging for invalid tracks in bulk lookup needs to be propagated

## Messaging

- `message` has been bumped to `BaseResponseModel`
  - endpoint services need to have a class member that is a list of messages; assign to response model in the `generate_response` function <- DONE
  - metadata query service needs to store messages as well (sharded collections)
