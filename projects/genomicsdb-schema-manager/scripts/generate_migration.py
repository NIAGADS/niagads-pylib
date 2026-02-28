#!/usr/bin/env python3
"""
Generate a database migration using Alembic autogenerate.

Usage:
    python generate_migration.py --message <message> [--schema <schema>]
"""

import argparse
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
    parser.add_argument(
        "--skip-fks",
        action="store_true",
        help=(
            "Skip foreign key generation. Required when the table involves a "
            "foreign key to another table that may not yet exist. Run the "
            "generator again without this flag after creating dependencies."
        ),
    )

    args = parser.parse_args()

    project_root = Settings.from_env().PROJECT_ROOT
    verify_path(project_root)

    cmd = [
        "poetry",
        "run",
        "alembic",
        "-c",
        path.join(project_root, "alembic.ini"),
    ]

    # Add optional xArgs
    if args.schema:
        cmd.extend(["-x", f"schema={args.schema}"])

    if args.skip_fks:
        cmd.extend(["-x ", "skipForeignKeys=true"])

    # Add revision command
    cmd.extend(["revision", "--autogenerate", f'-m "{args.message}"'])

    # Execute the command
    try:
        stdout = execute_cmd(cmd)
        print("Done. Please review and edit the generated migration file as needed.")
        print(stdout)
    except RuntimeError as err:
        print(f"Error: Migration generation failed")
        raise


if __name__ == "__main__":
    main()
