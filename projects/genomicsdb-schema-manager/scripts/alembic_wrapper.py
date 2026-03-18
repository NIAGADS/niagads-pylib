#!/usr/bin/env python3
"""
Wrap alembic calls to handle command line args and system environment.

Usage:
    python generate_migration.py --message <message> [--schema <schema>]
"""

import argparse
from os import path

from helpers.config import Settings
from niagads.database.genomicsdb.schema.base import GenomicsDBSchemaBase
from niagads.utils.logging import setup_root_logger
from niagads.common.core import ComponentBaseMixin
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.sys import create_dir, execute_cmd, verify_path, remove_path
from datetime import datetime
import uuid


class MigrationAction(CaseInsensitiveEnum):
    UPGRADE = "UPGRADE"
    DOWNGRADE = "DOWNGRADE"

    def __str__(self):
        return self.name.title()


class AlembicWrapper(ComponentBaseMixin):
    """
    Wrapper for alembic migration commands.

    Handles command construction and execution for alembic revision generation.
    """

    def __init__(self, schema: str, debug: bool = False, verbose: bool = False):
        super().__init__(debug, verbose)
        self._project_root = Settings.from_env().PROJECT_ROOT
        self.__schema = schema.lower() if schema is not None else schema
        verify_path(self._project_root)
        self._alembic_cmd_root = [
            "poetry",
            "run",
            "alembic",
            "-c",
            path.join(self._project_root, "alembic.ini"),
        ]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(project_root='{self._project_root}')"

    def create_schema_revision(self) -> None:
        """
        Create a manual Alembic revision file for schema creation (no autogenerate).
        """
        if self.__schema == "all":
            schemas = GenomicsDBSchemaBase.get_all_schemas()
        elif GenomicsDBSchemaBase.is_valid_schema(self.__schema):
            schemas = [self.__schema]
        else:
            raise ValueError(f"Invalid schema for GenomicsDB {self.__schema}")

        versions_dir = path.join(self._project_root, "alembic", "versions")
        revision_id = uuid.uuid4().hex[:12]
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        filename = f"{revision_id}_create_{self.__schema}_schema.py"
        filepath = path.join(versions_dir, filename)

        content = (
            f'"""Create {self.__schema} schema(s)\n\n'
            f"Revision ID: {revision_id}\n"
            f"Revises: \n"
            f'Create Date: {now}\n\n"""\n\n'
            "from alembic import op\n\n"
            f'revision = "{revision_id}"\n'
            "down_revision = None\n"
            "branch_labels = None\n"
            "depends_on = None\n\n"
            "def upgrade():\n"
            "    with op.get_context().autocommit_block():\n"
            + "".join(
                [
                    f'        op.execute("CREATE SCHEMA IF NOT EXISTS {schema}")\n'
                    for schema in schemas
                ]
            )
            + "\n"
            "def downgrade():\n"
            + "".join(
                [
                    f'        op.execute("DROP SCHEMA IF EXISTS {schema} CASCADE")\n'
                    for schema in schemas
                ]
            )
        )

        with open(filepath, "w") as f:
            f.write(content)
        self.logger.info(f"✓ Created manual schema migration: {filepath}")

    def reset(self):
        """resets alembic by removing all versions and deleting the alembic tables in the database
        cannot be reversed"""
        db_name = Settings.from_env().DATABASE_URI.split("/")[-1].split("?")[0]

        print(
            "\n⚠️  WARNING: This will delete all migration history from"
            f"database `{db_name}` and from the `$PROJECT_ROOT/alembic/versions` directory"
        )
        print("This action CANNOT be reversed.")

        confirmation = input(
            f"\nEnter the database name `{db_name}` to confirm: "
        ).strip()

        if confirmation != db_name:
            self.logger.info("Reset cancelled.")
            return

        try:
            self.logger.warning(
                f"DELETING all migration history from database `{db_name}`"
                "and from the `$PROJECT_ROOT/alembic/versions` directory"
            )

            # downgrade alembic_version table
            cmd = self._alembic_cmd_root.copy()
            cmd.extend(["downgrade", "base"])
            stdout = execute_cmd(cmd, print_cmd_only=self._debug, verbose=self._verbose)
            self.logger.info(f"✓ Alembic reset complete for database '{db_name}'.")

            # Remove versions directory
            versions_dir = path.join(self._project_root, "alembic", "versions")
            if path.exists(versions_dir):
                remove_path(versions_dir)
                create_dir(versions_dir)  # need to recreate
                self.logger.info(f"✓ Removed all versioning files in: {versions_dir}")

            self.logger.info(stdout)
        except RuntimeError as err:
            self.logger.exception(
                f"Alembic reset for database '{db_name}' failed.", exc_info=True
            )
        except Exception as err:
            self.logger.exception(
                f"Error removing versions directory: {err}", exc_info=True
            )

    def upgrade(self, revision: str):
        cmd = self._alembic_cmd_root.copy()

        if self.__schema:
            cmd.extend(["-x", f"schema={self.__schema}"])

        cmd.extend(["upgrade", revision])

        try:
            stdout = execute_cmd(cmd, print_cmd_only=self._debug, verbose=self._verbose)
            self.logger.info(f"Done - Ugrade to revision `{revision}` complete.")
            self.logger.info(stdout)
        except RuntimeError as err:
            self.logger.exception(
                f"Ugrade to revision `{revision}` failed.", exc_info=True
            )

    def downgrade(self, revision: str):
        cmd = self._alembic_cmd_root.copy()

        if self.__schema:
            cmd.extend(["-x", f"schema={self.__schema}"])

        cmd.extend(["downgrade", revision])

        try:
            stdout = execute_cmd(cmd, print_cmd_only=self._debug, verbose=self._verbose)
            self.logger.info(f"Done - Downgrade to revision `{revision}` complete.")
            self.logger.info(stdout)
        except RuntimeError as err:
            self.logger.exception(
                f"Downgrade to revision `{revision}` failed.", exc_info=True
            )

    def stamp(self, revision: str = "head"):
        """
        Stamp the database with a specific revision without running migrations.

        Args:
            revision (str): Revision identifier to stamp. Defaults to 'head'.
        """
        cmd = self._alembic_cmd_root.copy()
        cmd.extend(["stamp", revision])

        try:
            stdout = execute_cmd(cmd, print_cmd_only=self._debug, verbose=self._verbose)
            self.logger.info(f"Done - Stamp to revision `{revision}` complete.")
            self.logger.info(stdout)
        except RuntimeError as err:
            self.logger.exception(
                f"Stamp to revision `{revision}` failed.", exc_info=True
            )

    def generate_revision(self, message: str, skip_fks: bool = False) -> None:
        """
        Generate an alembic revision.

        Args:
            message (str): Migration message.
            skip_fks (bool): Skip foreign key generation. Defaults to False.

        Raises:
            RuntimeError: If migration generation fails.
        """
        cmd = self._alembic_cmd_root.copy()

        if self.__schema:
            cmd.extend(["-x", f"schema={self.__schema}"])

        if skip_fks:
            cmd.extend(["-x", "skipForeignKeys=true"])

        cmd.extend(["revision", "--autogenerate", f'-m "{message}"'])

        try:
            stdout = execute_cmd(cmd, print_cmd_only=self._debug, verbose=self._verbose)
            self.logger.info(
                "Done. Please review and edit the generated migration file as needed."
            )
            self.logger.info(stdout)
        except RuntimeError as err:
            self.logger.exception("Migration generation failed.", exc_info=True)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        "--schema",
        metavar="SCHEMA",
        help="Target schemal defaults to None",
    )
    parser.add_argument(
        "--message",
        metavar="MESSAGE",
        help="Migration message",
    )
    parser.add_argument(
        "--autogenerate",
        action="store_true",
        help="autogenrate a revision",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="reset alembic revision history; note - cannot be reversed",
    )
    parser.add_argument(
        "--upgrade",
        action="store_true",
        help="upgrade a revision",
    )
    parser.add_argument(
        "--downgrade",
        action="store_true",
        help="downgrade a revision",
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="stamp the database to a given revision without running migrations",
    )
    parser.add_argument(
        "--revision",
        default="head",
        help="revision number; defaults to `head` for ugrades, `-1` for downgrades",
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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--create-schema",
        action="store_true",
        help="Create a manual revision for schema creation",
    )

    args = parser.parse_args()

    setup_root_logger()

    wrapper = AlembicWrapper(args.schema, debug=args.debug, verbose=args.verbose)

    # List of mutually exclusive action argument names
    action_arg_names = [
        "autogenerate",
        "upgrade",
        "downgrade",
        "reset",
        "create_schema",
        "stamp",
    ]
    actions = [getattr(args, name) for name in action_arg_names]
    allowed_actions = [f"--{name.replace('_', '-')}" for name in action_arg_names]
    if sum(1 for x in actions if x) > 1:
        raise ValueError(
            "Cannot determine action. Specify only one of the following arguments:",
            ", ".join(allowed_actions),
        )
    if args.reset:
        wrapper.reset()
    if args.autogenerate:
        if not args.message:
            raise ValueError(
                "Must provide a message (`--message`) to describe a revision"
            )
        wrapper.generate_revision(args.message, skip_fks=args.skip_fks)
    if args.upgrade:
        wrapper.upgrade(revision=args.revision)
    if args.downgrade:
        wrapper.downgrade(revision="-1" if args.revision == "head" else args.revision)
    if args.stamp:
        # stamp uses the provided revision (defaults to head)
        wrapper.stamp(revision=args.revision)
    if args.create_schema:
        if not args.schema:
            raise ValueError("Must provide --schema for --create-schema option.")
        wrapper.create_schema_revision()


if __name__ == "__main__":
    main()
