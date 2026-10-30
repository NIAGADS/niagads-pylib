# NIAGADS Open Access Service

Python services and shared libraries supporting the [NIAGADS Open Access](https://www.niagads.org/) platform, including genomic data retrieval, annotation, API infrastructure, and data processing.

This repository uses a [Polylith architecture](https://polylith.gitbook.io/polylith) to organize reusable Python components and service entry points into independently packaged projects. It supports the backend infrastructure for accessing and interpreting Alzheimer's disease and related dementias (AD/ADRD) genomic data.

> **Development status:** This repository is under active development. Public-facing services and available data coverage may change as NIAGADS Open Access expands.

## Projects and Services

The repository contains independently configured Polylith projects that assemble shared components and bases into deployable services and applications.

### `genomicsdb-etl`

ETL infrastructure for processing genomic datasets and annotations for the NIAGADS Alzheimer's GenomicsDB and harmonized partner site data and metadata. Supports data ingestion, transformation, and loading into the underlying genomic data resources.

### `open-access-api`

FastAPI service providing structured, programmatic access to NIAGADS genomic records, annotations, and association evidence through REST endpoints.  Includes ASK NIAGADS, a natural-language querying layer that uses constrained agent orchestration, concept-based search, and validated API operations to retrieve and synthesize genomic evidence into source-grounded responses and interactive visualizations.

- [API documentation](https://api.niagads.org/docs)

### `niagads-metadata-validator`

Python package for JSON Schema-based validation of NIAGADS DSS submission metadata, including sample annotations and file manifests in tabular or Excel formats. Available as a command-line tool and importable Python module.

Published on [PyPI](https://pypi.org/project/niagads-metadata-validator/):

```bash
pip install niagads-metadata-validator
```

## Repository Architecture

The repository follows the [Python Polylith architecture](https://polylith.gitbook.io/polylith):

- **`components/`**: Reusable application logic and utilities.
- **`bases/`**: Application and service entry points.
- **`projects/`**: Independently configured packages, applications, and services assembled from shared bricks.

Individual projects define their own dependencies and package contents. See project-specific configurations and [CONTRIBUTING.md](./CONTRIBUTING.md) for development instructions.

## NIAGADS Open Access Resources

NIAGADS Open Access connects complementary AD/ADRD genomic resources, including:

- **Alzheimer's GenomicsDB:** Genetic associations, annotated variants, gene annotations, and genomic context.
- **FILER:** Functional genomics annotations and track metadata.
- **ADSP FunGen xQTL Atlas:** Molecular QTL evidence in relevant tissue and cell contexts.

## Partner Resources served through the Open Access API

- **ADVP:** Literature-curated AD/ADRD genetic associations.
- **TopGenes:** Expert-prioritized genes, variants, and loci with supporting evidence.

These resources describe the broader NIAGADS ecosystem; **not all of their data or functionality is exposed by the current API release**.

## Development and Contributing

For environment setup, Python/Poetry requirements, Polylith development, building and publishing projects, coding conventions, and troubleshooting, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## Related Projects and Documentation

- [NIAGADS Open Access Client](https://github.com/NIAGADS/open-access-client): Frontend applications, visualization components, and UI libraries.
- [Open Access Client Storybook](https://niagads.github.io/open-access-client/): Interactive component documentation and examples.
- [NIAGADS Open Access API](https://api.niagads.org/): Current deployment and ASK NIAGADS interface
- [NIAGADS](https://www.niagads.org/): NIAGADS resources and announcements.
