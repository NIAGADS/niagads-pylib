"""Print diff in metadata (all schemas) when model compared to database."""

import argparse
import pprint

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from helpers.config import Settings
from helpers.hooks import register_schemas
from niagads.genomicsdb.schema.core import GenomicsDBSchemaBase
from sqlalchemy import create_engine


def main():
    parser = argparse.ArgumentParser(
        description="Compare database schema with metadata definitions."
    )
    parser.add_argument(
        "schema",
        help="Schema name to compare",
    )

    args = parser.parse_args()

    # Load schema registry
    register_schemas()

    engine = create_engine(Settings.from_env().DATABASE_URI)

    mc = MigrationContext.configure(engine.connect())

    diff = compare_metadata(mc, GenomicsDBSchemaBase.metadata)
    pprint.pprint(diff, indent=2, width=20)


if __name__ == "__main__":
    main()
