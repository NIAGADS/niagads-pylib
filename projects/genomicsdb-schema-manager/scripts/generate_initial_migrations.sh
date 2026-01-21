#!/usr/bin/env bash

# Require ALEMBIC_ROOT to be set in the environment and point to a directory
if [ -z "$ALEMBIC_ROOT" ]; then
    echo "Error: ALEMBIC_ROOT environment variable is not set."
    return 10 2>/dev/null || true
fi
if [ ! -d "$ALEMBIC_ROOT" ]; then
    echo "Error: ALEMBIC_ROOT '$ALEMBIC_ROOT' does not exist or is not a directory."
    return 11 2>/dev/null || true
fi

echo "Generating initial migration for all schemas..."
if poetry run alembic -c $ALEMBIC_ROOT/../alembic.ini -x schema=ALL revision --autogenerate -m "initial all schemas and tables"; then
    echo "Done. Edit the generated migration files to add CREATE SCHEMA and required extensions as needed."
else
    echo "Alembic migration failed. Check the error above, fix any issues, and re-run the script as needed."
fi
