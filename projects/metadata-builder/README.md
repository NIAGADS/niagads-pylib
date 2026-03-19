# Track Metadata Builder

This project provides a Streamlit-based Track Metadata builder app for NIAGADS.

## Requirements

* git client
* Docker or Docker Desktop

## Installation

Use sparse checkout to clone only this project from the monorepo. 

```bash
git clone --filter=blob:none --sparse https://github.com/NIAGADS/niagads-pylib.git
cd niagads-pylib
git sparse-checkout init --cone
git sparse-checkout set --no-cone projects/metadata-builder
cd projects/metadata-builder
```

## Deploy with Docker

Use `docker compose` (**recommended**)

```bash
docker compose up
```

> **HINT**: add `-d` option to run in detached mode

or, build the image and run the container:

```bash
docker build -t metadata-builder .
docker run -p 8501:8501 metadata-builder
```

The app will be available at [http://localhost:8501](http://localhost:8501).
