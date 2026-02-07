# GenomicsDB Schema Inspector

A FastAPI-based web service for inspecting GenomicsDB tables through an intuitive form interface.

## Overview

The Schema Inspector provides a simple way to query database tables by schema, table name, and optionally filter by `run_id`. It displays up to 1000 rows of data in an easy-to-read table format.

## Features

- **Form-based Interface**: Select schema and table from dropdown menus
- **Run ID Filtering**: Optional filtering by ETL run ID for tables that have a `run_id` column
- **Automatic Schema Discovery**: Dynamically loads available schemas and tables from SQLAlchemy models registered in `SchemaRegistry`
- **Result Limiting**: Returns up to 1000 rows to prevent overwhelming the browser
- **Responsive Design**: Clean, modern UI that works on different screen sizes
- **Database Session Management**: Uses the existing `DatabaseSessionManager` for connection pooling

## Architecture (Polylith)

This project follows the Polylith architecture pattern:

- **Component** (`components/niagads/schema_inspector/`): Reusable utilities and Pydantic models
  - `utils.py`: Schema introspection functions
  - `models.py`: Request/response Pydantic models

- **Base** (`bases/niagads/schema_inspector_service/`): Business logic layer
  - `routes.py`: FastAPI route handlers

- **Project** (`projects/schema-inspector/`): Deployable artifact
  - `main.py`: Application entry point
  - `templates/`: Jinja2 HTML templates
  - `pyproject.toml`: Dependencies and package configuration

## Configuration

Create a `.env` file in the workspace root or set environment variables:

```bash
DATABASE_URI=postgresql://user:password@host:port/database
DEBUG=false
```

### Environment Variables

- `DATABASE_URI` (required): PostgreSQL connection string
- `DEBUG` (optional): Enable debug mode with SQL query logging (default: false)

## Installation

From the workspace root:

```bash
cd projects/schema-inspector
poetry install
```

## Usage

### Running the Service

```bash
# From the project directory
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### Accessing the Service

1. Open browser to `http://localhost:8080`
2. Select a schema from the dropdown (e.g., ADMIN, DATASET, GENE, REFERENCE, VARIANT)
3. Select a table from the second dropdown (populated based on schema selection)
4. Optionally enter a `run_id` to filter results
5. Click "Inspect Table" to view results

### API Endpoints

#### Web UI

- `GET /` - Display inspection form
- `POST /inspect` - Execute query and display results

#### API

- `GET /api/schemas` - Get available schemas and tables (JSON)
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## Dependencies

Core dependencies:

- **FastAPI**: Web framework
- **SQLAlchemy 2.x**: ORM and database queries
- **Pydantic v2**: Data validation
- **Jinja2**: HTML template rendering
- **asyncpg**: PostgreSQL async driver
- **python-multipart**: Form data parsing

## Development

The service integrates with existing niagads-pylib components:

- Uses `DatabaseSessionManager` for connection pooling
- Leverages `SchemaRegistry` for automatic schema discovery
- Follows project conventions for code style and documentation

### Running in Development Mode

```bash
# Enable debug mode and auto-reload
DATABASE_URI=postgresql://... DEBUG=true python main.py
```

## Limitations

- Results are limited to 1000 rows per query
- Only tables with a `run_id` column can be filtered by run ID
- Complex queries (joins, aggregations) are not supported through the UI
- Read-only access (no insert/update/delete operations)

## Schemas Supported

The inspector automatically discovers all schemas registered in `SchemaRegistry`:

- **ADMIN**: Administrative tables (ETL runs, etc.)
- **DATASET**: Track and collection metadata
- **GENE**: Gene annotations and structures
- **REFERENCE**: External databases, ontologies, pathways
- **VARIANT**: Variant data (if tables exist)
- **RAGDOC**: RAG document tables
