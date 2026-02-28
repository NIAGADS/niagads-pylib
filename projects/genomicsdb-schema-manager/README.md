# Alembic Database Schema Manager

Generic single-database configuration with an async dbapi

## Docker

### Setup

First, configure your environment by creating a `.env` file in this directory with the following **required variables**:

- `DATABASE_URI`: PostgreSQL connection string (required). If your database is running on localhost, use `host.docker.internal` instead of `localhost` to allow the container to access the host's network. Example: `postgresql://user:password@host.docker.internal:port/dbname`
- `SCHEMA_DEFS`: Python module path to schema definitions (optional, defaults to `niagads.genomicsdb.schemas`)
- `ALEMBIC_ROOT`: Absolute path to the alembic directory (required, needs to be set to `/app/alembic`)

### Build the Image

Build from the monorepo root:

```bash
cd ../..  # Navigate to niagads-pylib root
docker build -f projects/genomicsdb-schema-manager/Dockerfile -t genomicsdb-schema-manager:latest .
```

Or build with a specific tag:

```bash
docker build -f projects/genomicsdb-schema-manager/Dockerfile \
  -t genomicsdb-schema-manager:1.0.0 .
```

### Run with Docker Compose

Start the schema-manager service:

```bash
docker-compose up -d
```

This builds the image and starts the container with host network access to reach your database.

### Run Migrations Manually

Execute Alembic commands in the running container:

```bash
# Generate a new migration for a schema
docker-compose exec schema-manager alembic -x schema=<schema_name> revision --autogenerate -m "<comment>"

# Upgrade to latest
docker-compose exec schema-manager alembic -x schema=<schema_name> upgrade head

# Downgrade one revision
docker-compose exec schema-manager alembic -x schema=<schema_name> downgrade -1

# Check current revision
docker-compose exec schema-manager alembic -x schema=<schema_name> current

# Skip foreign key constraints during migration (useful for schema with circular FK dependencies)
docker-compose exec schema-manager alembic -x schema=<schema_name> -x skipForeignKeys upgrade head
```

### Stop and Clean Up

```bash
# Stop the container
docker-compose down

# Remove the container and rebuild
docker-compose down --rmi local
```

### Run Without Docker Compose

Execute a one-off migration directly:

```bash
docker run --rm \
  --network host \
  -e DATABASE_URI="postgresql://user:password@localhost:5432/genomicsdb" \
  -e SCHEMA_DEFS="niagads.genomicsdb.schemas" \
  -e ALEMBIC_ROOT="/app/alembic" \
  genomicsdb-schema-manager:latest \
  alembic -x schema=ALL upgrade head
```

### Image Details

The Docker image uses:

- **Base Image**: `python:3.12-slim` (requires Python 3.11+)
- **Multi-stage Build**: Reduces final image size by excluding build dependencies
- **Non-root User**: Runs as `appuser` (UID 1000) for enhanced security
- **Network**: Uses `host` mode to access PostgreSQL on the host machine
- **Included Tools**:
  - `alembic` - Database schema migrations
  - `gdb_run_sql` - Execute SQL scripts
  - `gdb_add_user` / `gdb_drop_user` - User management
  - `gdb_generate_migration` - Auto-generate migrations
  - `psql` - PostgreSQL client

## TODO

- for functions, views, triggers, etc use [alembic_utils](https://github.com/olirice/alembic_utils) (already added as depedency)

## Create schema and tables

Add schema, if necessary to `lib/schemas.py`.  Follow example of the Metadata model defintions to ensure that all tables are imported when the `<Schema>SchemaBase.metadata` is loaded.

Run the following to generate the code for the schema and table creation

```bash
alembic -x schema=<schema_name> revision --autogenerate -m "<comment>"
```

and then edit the resulting `alembic/versions/<revision>_<comment>.py` file to add the `CREATE SCHEMA` statement and any required extensions in the `upgrade` block.

e.g., from [alembic/versions/44faa8902d2b_initial_metadata_schema_and_tables.py](alembic/versions/44faa8902d2b_initial_metadata_schema_and_tables.py)

```python
op.execute("CREATE SCHEMA IF NOT EXISTS metadata")  # added by fossilfriend
op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")  # added by fossilfriend
```

Execute

```bash
alembic -x schema=<schema_name> upgrade head
```

to create the schema and tables.

To downgrade to previous state (rollback), run:

```bash
alembic -x schema=<schema_name> downgrade -1
```

## Trouble Shooting

### `Target database is not up to date`

Occurs when an PostGreSQL error interrupts the completion of an upgrade script (e.g., malformed index).

The head and current revision likely mismatch. You can check both by running the following:

```bash
alembic -x schema=<schema_name> current
alembic -x schema=<schema_name> heads
```

To resolve this issue and set the `HEAD` to the current revision, run the following:

```bash
alembic -x schema=<schema_name> stamp heads
```
