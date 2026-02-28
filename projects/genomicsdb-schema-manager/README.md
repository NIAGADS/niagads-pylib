# Database Schema Manager

Generic single-database configuration with an async dbapi

For most schema-management tasks there should be no need to run `alembic` or `psql` commands directly.  The following scripts are available:

- `generate_migration.py`: generates an alembic migration
-

## Environment

Create a `.env` file or set the following environemntal variables:

- `DATABASE_URI`: PostgreSQL connection string (required). If your database is running on localhost, use `host.docker.internal` instead of `localhost`. Example: `postgresql://user:password@host.docker.internal:port/dbname`
- `SCHEMA_DEFS`: Python module path to schema definitions (optional, defaults to `niagads.genomicsdb.schemas`)
- `ALEMBIC_ROOT`: Absolute path to the alembic directory (required, typically `/app/alembic`)
