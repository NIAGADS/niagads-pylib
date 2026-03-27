#!/usr/bin/env python3
"""
Create a database user and grant them a database role.

Usage:
    python create_db_user.py --user <username> --role <role> [--database-uri <uri>]
"""

import argparse
import asyncio
import secrets
import string

from niagads.arg_parser.core import case_insensitive_enum_type
from niagads.database import DatabaseSessionManager

from helpers.config import Settings
from helpers.types import DBRole


async def run():
    """Parse arguments and create the user."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        "--user",
        required=True,
        metavar="USERNAME",
        help="username to create",
    )
    parser.add_argument(
        "--role",
        required=True,
        metavar="ROLE",
        type=case_insensitive_enum_type(DBRole),
        help=f"database role to grant; choices: {', '.join(DBRole.list())}",
    )
    parser.add_argument(
        "--database-uri",
        metavar="URI",
        help="PostgreSQL connection URI; if not set, reads DATABASE_URI from .env",
    )

    args = parser.parse_args()

    # Get connection string
    connection_string = (
        args.database_uri
        if args.database_uri is not None
        else Settings.from_env().DATABASE_URI
    )

    # Initialize database session manager
    session_manager = DatabaseSessionManager(connection_string)

    # Convert role value back to enum
    role = DBRole(args.role)

    # Generate password
    password = "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(8)
    )

    # Use raw connection for multiple statements
    async with session_manager.raw_connection() as conn:
        # Create user
        sql = f"""
            CREATE USER "{args.user}" WITH PASSWORD '{password}';
        """
        await conn.execute(sql)

        # Grant role to user
        grant_role_sql = f'GRANT {role} TO "{args.user}";'
        await conn.execute(grant_role_sql)

        # commit
        await conn.commit()

    await session_manager.close()

    print(f"Done - created {str(role).upper()} user `{args.user}` : {password}")


def main():  # handle poetry script usage / poetry calls main directly
    asyncio.run(run())


if __name__ == "__main__":
    main()
