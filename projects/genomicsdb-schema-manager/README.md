# Database Schema Manager

Generic single-database configuration with an async dbapi

For most schema-management tasks there should be little or no need to run `alembic` or `psql` commands directly.  The following scripts are available:

- `gdb_generate_migration`: generates an alembic migration
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

### New Database Initialization

See [README](./initialize-db/README.md) in the `initialize-db` directory.
