from sqlalchemy import Connection, Table, event


def register_schema_creation():
    """Register global event to auto-create schemas for tables with .schema set."""

    def ensure_schema(target: Table, connection: Connection, **kw):
        schema = target.schema
        if schema:
            connection.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')

    event.listen(Table, "before_create", ensure_schema)
