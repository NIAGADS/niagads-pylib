# Track Metadata Builder

This project provides a Streamlit-based Track Metadata builder app for NIAGADS.

## Requirements

* git client
* Docker or Docker Desktop

## Installation

Use sparse checkout to clone only this project from the monorepo. There are two common approaches depending on your Git version.

```bash
git clone --filter=blob:none --sparse https://github.com/NIAGADS/niagads-pylib.git
cd niagads-pylib
git sparse-checkout set projects/metadata-builder
```

## Deploy with Docker

Use `docker compose` (**recommended**)

```bash
docker compose up --build
```

or, build the image and run the container:

```bash
docker build -t metadata-builder .
docker run -p 8501:8501 metadata-builder
```

The app will be available at [http://localhost:8501](http://localhost:8501).
