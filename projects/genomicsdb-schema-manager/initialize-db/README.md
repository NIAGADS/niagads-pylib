# Initialize a new GenomicsDB Database Instance

## Requirements

- `PostgreSQL` >= 18
- `pgvector`
- `Apache AGE`
- `plpython`

## Bootstrap Database

Run the bootstrap script to create extensions and roles.

```bash
source $PROJECT_ROOT/initialize-db/boostrap_db.sh --commit
```

where `$PROJECT_ROOT` is the full path to the `genomicsdb-schema-manager` project.

## Initial Alembic Migration - No Version Files Exist

If building from already generated [version](../alembic/versions/) files, see [TBA]

### Alembic Environment

Alembic needs the following environmental variables:

- `DATABASE_URI` - database connection string in the format `postgresql://user:password@host:port/database`
- `SCHEMA_DEFS` - (optional) for the schema registry, defaults to `niagads.genomicsdb.schema`
- `PROJECT_ROOT`- the full path to the `genomicsdb-schema-manager` project

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

#### Step3.  Create the Partioned Variant Tables

Although there are SQLAlchemy models defining Variant.Variant, the table is partitioned and Alembic cannot handle that easily.  So just create using SQL.

```bash
source $PROJECT_ROOT/initialize-db/create_partitioned_variant_tables.sh
```

#### Step 4. Create `Admin` Helpers

These commands will create DBAdmin Helper Views and Functions for tasks such as like lock and table Size monitoring, a lookup for user defined functions, estimating result sizes, etc.

```bash
source $PROJECT_ROOT/initialize-db/create_admin_views.sh --commit
```

#### `Admin` Views

### Step 2. `All` Schema Revision - no Foreign Keys

### Step 3. Foreign Keys

### Step 4. Functions

### Stpe 5. Graph Schema
