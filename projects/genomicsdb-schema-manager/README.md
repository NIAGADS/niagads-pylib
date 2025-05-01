# Alembic Database Schema Manager

Generic single-database configuration with an async dbapi

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