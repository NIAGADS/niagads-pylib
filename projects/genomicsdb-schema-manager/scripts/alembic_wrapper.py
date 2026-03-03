#!/usr/bin/env python3
"""
Wrap alembic calls to handle command line args and system environment.

Usage:
    python generate_migration.py --message <message> [--schema <schema>]
"""

import argparse
from os import path

from helpers.config import Settings
from niagads.common.core import ComponentBaseMixin
from niagads.enums.core import CaseInsensitiveEnum
from niagads.utils.sys import execute_cmd, verify_path


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
        self.__schema = schema
        verify_path(self._project_root)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(project_root='{self._project_root}')"

    def upgrade(self, revision: str):
        cmd = ["alembic"]
        if self.__schema:
            cmd.extend(["-x", f"schema={self.__schema}"])
        cmd.extend("upgrade", revision)
        try:
            stdout = execute_cmd(cmd, print_cmd_only=self._debug, verbose=self._verbose)
            self.logger.info(f"Done - Ugrade to revision `{revision}` complete.")
            self.logger.info(stdout)
        except RuntimeError as err:
            self.logger.exception(
                f"Ugrade to revision `{revision}` failed.", exc_info=True
            )

    def downgrade(self, revision: str):
        cmd = ["alembic"]
        if self.__schema:
            cmd.extend(["-x", f"schema={self.__schema}"])
        cmd.extend("downgrade", revision)
        try:
            stdout = execute_cmd(cmd, print_cmd_only=self._debug, verbose=self._verbose)
            self.logger.info(f"Done - Downgrade to revision `{revision}` complete.")
            self.logger.info(stdout)
        except RuntimeError as err:
            self.logger.exception(
                f"Downgrade to revision `{revision}` failed.", exc_info=True
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
        cmd = [
            "poetry",
            "run",
            "alembic",
            "-c",
            path.join(self._project_root, "alembic.ini"),
        ]

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
        required=True,
        metavar="MESSAGE",
        help="Migration message",
    )
    parser.add_argument(
        "--autogenerate",
        action="store_true",
        help="autogenrate a revision",
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

    args = parser.parse_args()

    wrapper = AlembicWrapper(args.schema, debug=args.debug, verbose=args.verbose)

    actions = [args.autogenerate, args.upgrade, args.downgrade]
    if sum(1 for x in actions if x) > 1:
        raise ValueError(
            "Cannot determine action.  Specify only one of the following arguments:",
            "`--upgrade`, `--downgrade`, `--autogenerate`",
        )

    if args.autogenerate:
        wrapper.generate_revision(args.message, skip_fks=args.skip_fks)
    if args.upgrade:
        wrapper.upgrade(revision=args.revision)
    if args.downgrade:
        wrapper.downgrade(revision="-1" if args.revision == "head" else args.revision)


if __name__ == "__main__":
    main()
