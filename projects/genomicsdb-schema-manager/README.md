# Database Schema Manager

Generic single-database configuration with an async dbapi

For most schema-management tasks there should be little or no need to run `alembic` or `psql` commands directly.  The following scripts are available:

- `gdb_alembic`: alembic wrapper
- `gdb_metadata_diff`: compare metadata model to database schema for a given schema
- `gdb_add_user`: create a database user
- `gdb_drop_user`: remove a database user
- `gdb_run_sql`: executes a SQL file

## Usage

### Environment Setup

Create a `.env` file or set the following environemntal variables:

- `DATABASE_URI`: PostgreSQL connection string (required). If your database is running on localhost, use `host.docker.internal` instead of `localhost`. Example: `postgresql://user:password@host.docker.internal:port/dbname`
- `SCHEMA_DEFS`: Python module path to schema definitions (optional, defaults to `niagads.genomicsdb.schemas`)
- `ALEMBIC_ROOT`: Absolute path to the alembic directory (required, typically `/app/alembic`)
- `PROJECT_ROOT`: Absolute path to the `genomicsdb-schema-manager` project

To avoid conflict with main monorepo install, run these in the project root using Poetry as follows:

```bash
cd $PROJECT_ROOT
poetry run <script> <options>
```

### New Database Initialization

See [README](./initialize-db/README.md) in the `initialize-db` directory.

### `gdb_alembic` Usage

`gdb_alembic` is a wrapper script for Alembic database migrations, providing a streamlined interface for common schema management tasks. Run all commands from the project root using Poetry:

```bash
poetry run gdb_alembic <options>
```

#### Options

- `--schema <schema>`: Target schema (required for schema-specific actions)
- `--message <msg>`: Migration message (required for revision generation)
- `--autogenerate`: Generate a new migration (autogenerate from models)
- `--create-schema`: Create a manual revision for schema creation
- `--upgrade`: Apply migrations up to a revision (default: head)
- `--downgrade`: Revert migrations (default: downgrade to previous mgiration)
- `--reset`: Remove all migration history (irreversible)
- `--stamp`: Mark the database with a specific revision without running migrations
- `--revision <rev>`: Specify revision (default: head for upgrade/stamp, -1 for downgrade)
- `--debug`, `--verbose`: Enable debug or verbose output

#### Examples

Generate a new migration (autogenerate):

```bash
poetry run gdb_alembic --schema my_schema --autogenerate --message "Add new table"
```

Create a manual schema revision:

```bash
poetry run gdb_alembic --schema my_schema --create-schema
```

Upgrade to latest revision:

```bash
poetry run gdb_alembic --schema my_schema --upgrade
```

Reset all migration history (DANGEROUS):

```bash
poetry run gdb_alembic --reset
```
