# Initialize a new GenomicsDB Database Instance

## Requirements

- `PostgreSQL` >= 18
- `pgvector`
- `Apache AGE`
- `plpython`

## Set Project Root

Set `PROJECT_ROOT` to the full path to the `genomicsdb-schema-manager` project.

## Bootstrap Database

Run the bootstrap script to create extensions and roles.

```bash
source $PROJECT_ROOT/initialize-db/boostrap_db.sh --commit
```

## Initial Alembic Migration - No Version Files Exist

### Alembic Environment

In addition to `PROJECT_ROOT` Alembic needs the following environmental variables.

- `DATABASE_URI` - database connection string in the format `postgresql://user:password@host:port/database`
- `SCHEMA_DEFS` - (optional) for the schema registry, defaults to `niagads.genomicsdb.schema`

Create a `.env` file with the following or set as system environmental variables.  **Note**: System variables will override anything in the `.env` file.

### Step 1. Create the Schemas

```bash
poetry run gdb_alembic --schema All --create-schema
poetry run gdb_alembic --upgrade 
```

#### Step 2. Generate the initial migration

```bash
poetry run gdb_alembic --schema All --message "initial table creation - all schemas" --autogenerate
poetry run gdb_alembic --upgrade 
```

#### `Admin` Functions

#### `Admin` Views

### Step 2. `All` Schema Revision - no Foreign Keys

### Step 3. Foreign Keys

### Step 4. Functions

### Stpe 5. Graph Schema
