#!/usr/bin/env python3
"""
Generate a database migration using Alembic autogenerate.

Usage:
    python generate_migration.py --message <message> [--schema <schema>]
"""

import argparse
import sys
from os import path

from helpers.config import Settings
from niagads.utils.sys import execute_cmd, verify_path


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        "--schema",
        metavar="SCHEMA",
        help="Target schema (default: ALL)",
    )
    parser.add_argument(
        "--message",
        required=True,
        metavar="MESSAGE",
        help="Migration message",
    )

    args = parser.parse_args()

    alembic_root = Settings.from_env().ALEMBIC_ROOT
    verify_path(alembic_root)

    cmd = ["poetry", "run", "alembic", "-c", path.join(alembic_root, "alembic.ini")]

    # Add optional schema filter
    if args.schema:
        cmd.extend(["-x", f"schema={args.schema}"])

    # Add revision command
    cmd.extend(["revision", "--autogenerate", "-m", args.message])

    # Execute the command
    try:
        execute_cmd(cmd)
        print("Done. Please review and edit the generated migration file as needed.")
    except Exception as err:
        raise


if __name__ == "__main__":
    main()
