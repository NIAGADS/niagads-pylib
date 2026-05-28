# TODOs

## Bugs

### FILER Track Metadata Brief Response

- `data_category` is always null
- `is_download_only` should be `True` or `False` not `null`
  
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

- messaging for invalid tracks in bulk lookup needs to be propagated
