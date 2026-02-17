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


# Usage/help
usage() {
    echo "Usage: $0 [-s|--schema <schema>] [-m|--message <message>]"
    echo "  -s, --schema   Target schema (default: ALL)"
    echo "  -m, --message  Migration message (default: 'initialize all schemas (non admin) and tables')"
    echo "  -h, --help     Show this help message"
}


# Required args (no defaults)
SCHEMA=""
MESSAGE=""

# Parse args
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -s|--schema)
            SCHEMA="$2"
            shift; shift
            ;;
        -m|--message)
            MESSAGE="$2"
            shift; shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Require both SCHEMA and MESSAGE
if [[ -z "$SCHEMA" || -z "$MESSAGE" ]]; then
    echo "Error: Both --schema and --message are required."
    usage
    exit 2
fi

echo "Generating migration for schema: $SCHEMA"
echo "Migration message: $MESSAGE"
if poetry run alembic -c "$ALEMBIC_ROOT/../alembic.ini" -x schema="$SCHEMA" revision --autogenerate -m "$MESSAGE"; then
    echo "Done. Edit the generated migration files to add CREATE SCHEMA and required extensions as needed."
else
    echo "Alembic migration failed. Check the error above, fix any issues, and re-run the script as needed."
fi
