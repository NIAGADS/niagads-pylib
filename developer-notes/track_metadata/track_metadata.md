# TrackRecord metadata

`TrackRecord` is the canonical metadata model for a NIAGADS genomic data track. It identifies the track, describes the file and experiment, records where the data came from, and provides biological context such as phenotypes, biosamples, and curation history.

The accompanying [`track_record.schema.json`](track_record.schema.json) is generated from the Pydantic `TrackRecord` model. It is intended for validating metadata exchanged with or loaded into NIAGADS.

## A brief introduction to JSON Schema

[JSON Schema](https://json-schema.org/) is a standard vocabulary for describing and validating JSON documents. The [Understanding JSON Schema guide](https://json-schema.org/understanding-json-schema/) is a useful introduction, and [Pydantic's JSON Schema documentation](https://docs.pydantic.dev/latest/concepts/json_schema/) explains how schemas are generated from Pydantic models.

Only a few JSON Schema concepts are needed to read this schema:

| Keyword | Meaning in the TrackRecord schema |
| --- | --- |
| `properties` | Fields belonging to an object. The root `properties` are the fields on `TrackRecord`. |
| `required` | Fields that must be supplied. A field not listed here may be omitted. |
| `$defs` | Reusable definitions for nested models and enums. |
| `$ref` | A link to one of those definitions. For example, `#/$defs/Provenance` means the `Provenance` definition in this file. |
| `type` | The JSON type: `string`, `integer`, `boolean`, `array`, `object`, or `null`. |
| `anyOf` | The value may match any listed alternative. Pydantic commonly uses this for a value that may also be `null`. |
| `enum` | The allowed values for a controlled vocabulary. |
| `items` | The schema for every value in an array. |
| `default` | The value Pydantic uses if the field is omitted. |

Definitions are separated to avoid repeating large nested schemas. For example, the root property `shard_chromosome` contains a `$ref` to `#/$defs/HumanGenome`; the `HumanGenome` definition supplies its allowed chromosome values.

## TrackRecord fields

The generated schema describes validation input. The `Internal?` column identifies fields excluded from normal serialization by the current Pydantic configuration. Internal fields remain documented because they are part of model validation, but they are omitted from the serialized examples.

| Field | JSON shape | Required? | Internal? | Purpose |
| --- | --- | --- | --- | --- |
| `id` | string | Yes | No | Stable public track identifier. When mapping the supplied database record, use `source_id` here; do not expose the database primary key `track_id`. |
| `name` | string | Yes | No | Human-readable track name. |
| `description` | string or null | No | No | Summary of the data represented by the track. |
| `genome_build` | `GenomeBuild` enum | No | No | Reference assembly. Defaults to `GRCh38`. |
| `keywords` | array of `OntologyTerm` or null | No | No | MeSH topical descriptors for discovery and search. This field is new in the revised model. |
| `feature_type` | `GenomicFeatureType` enum or null | No | No | Primary genomic feature, such as `VARIANT` or `REGION`. |
| `is_download_only` | boolean or null | No | No | Indicates that the file can be downloaded but its data cannot be queried through the Open Access API. |
| `is_shard` | boolean or null | No | **Yes** | Indicates that the record is one chromosome shard. |
| `shard_chromosome` | `HumanGenome` enum or null | No | **Yes** | Chromosome assigned to a shard. |
| `cohorts` | array of strings or null | No | No | Study cohorts represented by the track. |
| `provenance` | `Provenance` object | Yes | No | Source, accession, release, publication, and attribution metadata. Nested fields can have their own serialization rules. |
| `file_properties` | `FileProperties` object | Yes | No | Physical and structural metadata for the track file. |
| `experimental_design` | `ExperimentalDesign` object or null | No | No | Assay, analysis, classification, output, and covariate information. |
| `participant_phenotypes` | `Phenotype` object or null | No | No | Disease and participant demographic or biological characteristics. |
| `study_diagnosis` | array of `PhenotypeCount` or null | No | No | Case and control counts by phenotype. |
| `biosample_characteristics` | `BiosampleCharacteristics` object or null | No | No | Biosample, biosample type, tissue, system, biomarker, and life-stage annotations. |
| `curation_history` | array of `CurationEvent` or null | No | No | Chronological record of processing and curation actions. |

The four required root fields are `id`, `name`, `provenance`, and `file_properties`.

## Nested metadata

### Provenance

| Field | JSON shape | Required? | Internal? | Purpose |
| --- | --- | --- | --- | --- |
| `data_source` | string | No | No | Original data provider, such as `3DGenome` or `NIAGADS_DSS`. |
| `accession` | string or null | No | No | Accession assigned by the source. |
| `release_date` | string or null | No | No | Date on which this version of the source data was released. |
| `release_version` | string or null | No | No | Version label assigned to the source data release. |
| `download_date` | string or null | No | No | Date NIAGADS obtained the source data. |
| `download_url` | string or null | No | **Yes** | Original download location. |
| `consortium` | array of `Consortia` enums or null | No | No | Controlled list of contributing consortia. |
| `study` | string or null | No | No | Study from which the track data originated. |
| `project` | string or null | No | No | Larger program or project under which one or more studies or datasets are organized. |
| `attribution` | string or null | No | No | Author-year attribution, for example `Kang et al. 2024`. |
| `pubmed_id` | array of strings or null | No | No | Unique set of eight-digit PubMed identifiers. |
| `doi` | array of strings or null | No | No | Unique set of publication DOIs. |
| `data_source_url` | string | No | No | Computed from `data_source` and included in serialized output; it is not supplied as model input. |

### File properties

| Field | JSON shape | Required? | Internal? | Purpose |
| --- | --- | --- | --- | --- |
| `file_name` | string | Yes | No | File name. |
| `md5sum` | string | Yes | No | MD5 checksum constrained to the checksum pattern. |
| `file_size` | integer | Yes | No | File size in bytes. |
| `url` | string or null | No | No | Public or controlled-access file URL. |
| `bp_covered` | integer or null | No | No | Number of genomic base pairs covered. |
| `num_intervals` | integer or null | No | No | Number of genomic intervals in the file. |
| `file_format` | string or null | No | No | General format, such as `bed`. |
| `file_schema` | string or null | No | No | More specific column layout, such as `bed4+19|interact`. |
| `release_date` | string or null | No | No | Release date for this particular file. |

### Experimental design

| Field | JSON shape | Required? | Internal? | Purpose |
| --- | --- | --- | --- | --- |
| `antibody_target` | string or null | No | No | Molecule targeted by the assay antibody, when applicable. |
| `assay` | string or null | No | No | Experimental assay used to generate the data. |
| `analysis` | string or null | No | No | Analysis method or workflow applied to the experimental data. |
| `classification` | string or null | No | No | Track classification used to organize related experimental outputs. |
| `data_category` | string or null | No | No | Broad category describing the type of data. |
| `output_type` | string or null | No | No | Specific kind of result produced by the experiment or analysis. |
| `is_lifted` | boolean or null | No | No | Whether coordinates were lifted from an earlier genome build. |
| `covariates` | array of `OntologyTerm` or null | No | No | Variables included as analysis covariates. |

### Participant phenotypes

Each field is an independent array of ontology terms; the categories are not interchangeable.

| Field | JSON shape | Required? | Internal? | Purpose |
| --- | --- | --- | --- | --- |
| `disease` | array of `OntologyTerm` or null | No | No | Disease diagnoses or disease states represented among participants. |
| `neuropathology` | array of `OntologyTerm` or null | No | No | Neuropathological findings or classifications. |
| `symptom` | array of `OntologyTerm` or null | No | No | Observed or reported health characteristics. |
| `ethnicity` | array of `OntologyTerm` or null | No | No | Cultural, linguistic, or national-origin identity. |
| `race` | array of `OntologyTerm` or null | No | No | Broad social or historical classification, which may be self-identified. |
| `population` | array of `OntologyTerm` or null | No | No | Genetic ancestry, geography, or shared evolutionary-history population. |
| `genotype` | array of `OntologyTerm` or null | No | No | Genotype-based participant classification. |
| `gender` | array of `OntologyTerm` or null | No | No | Gender annotation for the represented participants. |

### Study diagnosis

Each object in `study_diagnosis` is a `PhenotypeCount`.

| Field | JSON shape | Required? | Internal? | Purpose |
| --- | --- | --- | --- | --- |
| `phenotype` | array of `OntologyTerm` or null | No | No | Diagnosis or phenotype being counted. |
| `num_cases` | integer | Yes | No | Number of participants classified as cases for this phenotype. |
| `num_controls` | integer or null | No | No | Number of participants classified as controls for this phenotype. |

### Biosample characteristics

| Field | JSON shape | Required? | Internal? | Purpose |
| --- | --- | --- | --- | --- |
| `biosample` | array of `OntologyTerm` or null | No | No | Biological samples represented by the track. |
| `biosample_type` | array of `BiosampleType` enums or null | No | No | Controlled biosample types, such as cell line or tissue. |
| `biomarker` | array of `OntologyTerm` or null | No | No | Measured or selected biomarkers. |
| `system` | array of strings or null | No | No | Anatomical or biological system labels. |
| `tissue` | array of `OntologyTerm` or null | No | No | Tissues represented by the samples. |
| `life_stage` | `OntologyTerm` object or null | No | No | Donor or sample life stage. |

### Curation history

Each object in `curation_history` is a distinct `CurationEvent`.

| Field | JSON shape | Required? | Internal? | Purpose |
| --- | --- | --- | --- | --- |
| `event_date` | string | Yes | No | Date on which the curation or processing event occurred. |
| `event_type` | `CurationEventType` enum | No | No | Controlled event category, such as `STANDARDIZE`, `VALIDATE`, or `FILTER`. |
| `actor` | string or null | No | No | Name of the user, service, or organization that performed the event. |
| `actor_type` | `CurationActorType` enum or null | No | No | Identifies the actor as a `USER`, `SERVICE`, or `PIPELINE`. |
| `tool` | string or null | No | No | Software or pipeline used for the event. |
| `tool_version` | string or null | No | No | Version of that software or pipeline. |

### Ontology terms and enums in serialized output

In the serialized examples below, an ontology term is represented only by its human-readable `term` and stable `curie`:

```json
{
  "term": "Alzheimer's disease",
  "curie": "EFO:1001870"
}
```

Enums are serialized by enum name. Examples include `GRCh38`, `VARIANT`, `REGION`, `STANDARDIZE`, and `USER`. The validation schema's `$defs` section lists each enum's accepted values, which may use a different case from the serialized names (for example, validation value `variant` and serialized name `VARIANT`).

## Serialized example: 3DGenome track

This output is based on the supplied database record. The public `source_id` becomes `id`; database-only columns are not part of the representation. Nulls are retained in this example.

```json
{
  "id": "NGTDGZBQ7JUPUP",
  "name": "3DGenome H1-hESC Hi-C chromatin interactions",
  "description": "3DGenome H1-hESC Hi-C chromatin interactions (bed4+19 interact) [Life stage: Embryonic]",
  "genome_build": "GRCh38",
  "keywords": null,
  "feature_type": "REGION",
  "is_download_only": null,
  "cohorts": null,
  "provenance": {
    "data_source": "3DGenome",
    "accession": null,
    "release_date": null,
    "release_version": null,
    "download_date": "2023-02-13",
    "consortium": null,
    "study": null,
    "project": null,
    "attribution": null,
    "pubmed_id": null,
    "doi": null,
    "data_source_url": "https://3dgenome.fsm.northwestern.edu"
  },
  "file_properties": {
    "file_name": "formatted_output_Dixon_2015_H1-ESC_hg38_peakachu_merged_loops.bed.gz",
    "url": "https://tf.lisanwanglab.org/GADB/FILER2/Annotationtracks/3DGenome/Hi-C/bed4plus19_interact/hg38/formatted_output_Dixon_2015_H1-ESC_hg38_peakachu_merged_loops.bed.gz",
    "md5sum": "2c0d0bf476f4dfbb5cf01da4f282b709",
    "bp_covered": 257410000,
    "num_intervals": null,
    "file_size": 1011550,
    "file_format": "bed",
    "file_schema": "bed4+19|interact",
    "release_date": "2024-10-04"
  },
  "experimental_design": {
    "antibody_target": null,
    "assay": "Hi-C",
    "analysis": null,
    "classification": "Hi-C chromatin interactions",
    "data_category": "chromatin interactions",
    "output_type": "chromatin interactions",
    "is_lifted": false,
    "covariates": null
  },
  "participant_phenotypes": null,
  "study_diagnosis": null,
  "biosample_characteristics": {
    "biosample": [
      {
        "term": "H1-hESC",
        "curie": "#FILER-biosample:H1-hESC"
      }
    ],
    "biosample_type": [
      {
        "term": "cell line",
        "curie": "CLO:0000031"
      }
    ],
    "biomarker": null,
    "system": [
      "Stem Cell"
    ],
    "tissue": [
      {
        "term": "Stem Cell",
        "curie": "#FILER-tissue:Stem Cell"
      }
    ],
    "life_stage": {
      "term": "Embryonic",
      "curie": "FILER-lifestage:Embryonic"
    }
  },
  "curation_history": null
}
```

## Serialized example: NIAGADS GWAS track

This example demonstrates the phenotype, diagnosis, covariate, publication, cohort, and curation fields that are empty in the 3DGenome record.

```json
{
  "id": "NG00182_0AED396A_STD",
  "name": "Novel Alzheimer's Disease Risk Loci in Korean participants: Female",
  "description": "GWAS summary statistics from single-variant association tests for WGS data from 1,980 female Koreans aged 60 years or older.",
  "genome_build": "GRCh38",
  "keywords": null,
  "feature_type": "VARIANT",
  "is_download_only": null,
  "cohorts": [
    "GARD"
  ],
  "provenance": {
    "data_source": "NIAGADS_DSS",
    "accession": "NG00182",
    "release_date": "2025-09-24",
    "release_version": "v1",
    "download_date": null,
    "consortium": null,
    "study": null,
    "project": null,
    "attribution": "Kang et al. 2024",
    "pubmed_id": [
      "39428694"
    ],
    "doi": [
      "10.1002/alz.14128"
    ],
    "data_source_url": "https://dss.niagads.org"
  },
  "file_properties": {
    "file_name": "NG00182_0AED396A_STD.tsv.gz",
    "url": null,
    "md5sum": "552a93b3823239a0642bb01de1e505af",
    "bp_covered": null,
    "num_intervals": null,
    "file_size": 710837617,
    "file_format": null,
    "file_schema": null,
    "release_date": null
  },
  "experimental_design": {
    "antibody_target": null,
    "assay": null,
    "analysis": null,
    "classification": null,
    "data_category": "GWAS Summary Statistics",
    "output_type": null,
    "is_lifted": false,
    "covariates": [
      {
        "term": "gender",
        "curie": "NCIT:C17357"
      }
    ]
  },
  "participant_phenotypes": {
    "disease": [
      {
        "term": "Alzheimer's disease",
        "curie": "EFO:1001870"
      }
    ],
    "neuropathology": null,
    "symptom": null,
    "ethnicity": null,
    "race": [
      {
        "term": "Asian",
        "curie": "HANCESTRO:0008"
      }
    ],
    "population": [
      {
        "term": "Korean",
        "curie": "HANCESTRO:0022"
      }
    ],
    "genotype": null,
    "gender": [
      {
        "term": "female",
        "curie": "PATO:0000383"
      }
    ]
  },
  "study_diagnosis": [
    {
      "phenotype": [
        {
          "term": "Alzheimer's disease",
          "curie": "EFO:1001870"
        }
      ],
      "num_cases": 914,
      "num_controls": 1066
    }
  ],
  "biosample_characteristics": null,
  "curation_history": [
    {
      "event_date": "2026-05-10",
      "event_type": "STANDARDIZE",
      "actor": "NIAGADS",
      "actor_type": "USER",
      "tool": "hipFG",
      "tool_version": "1.4.1"
    }
  ]
}
```

## Null handling

The examples retain nulls to make the complete shape easier to see. Pydantic can omit fields whose value is `None` by setting `exclude_none=True`:

```python
serialized = track_record.model_dump(
    mode="json",
    exclude_none=True,
    context={SerializationOptions.ENUMS_AS_NAME: True},
)
```

This changes only the output representation; it does not change the model or the generated validation schema.

## Regenerating the schema

The schema is generated directly from the model:

```python
import json

from niagads.common.track.models.record import TrackRecord

schema = TrackRecord.model_json_schema()
print(json.dumps(schema, indent=2))
```

Because this is a validation schema, it includes all declared `TrackRecord` fields, including `is_shard` and `shard_chromosome`.
