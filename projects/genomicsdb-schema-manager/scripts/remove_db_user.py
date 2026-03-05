#!/usr/bin/env python3
"""
Remove a database user from the database.

Usage:
    python remove_db_user.py --user <username> [--database-uri <uri>]
"""

import argparse
import asyncio
from sqlalchemy import text

from niagads.database import DatabaseSessionManager
from helpers.config import Settings


async def run():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        "--user",
        required=True,
        metavar="USERNAME",
        help="username to remove",
    )
    parser.add_argument(
        "--database-uri",
        metavar="URI",
        help="PostgreSQL connection URI; if not set, reads DATABASE_URI from .env",
    )

    args = parser.parse_args()

    connection_string = (
        args.database_uri
        if args.database_uri is not None
        else Settings.from_env().DATABASE_URI
    )

    session_manager = DatabaseSessionManager(connection_string)

    # Retrieve user's roles using a SQLAlchemy session
    async with session_manager.session_ctx() as session:
        result = await session.execute(
            text(
                """
                SELECT r.rolname
                FROM pg_auth_members m
                JOIN pg_roles r ON m.roleid = r.oid
                JOIN pg_roles u ON m.member = u.oid
                WHERE u.rolname = :username
                """
            ),
            {"username": args.user},
        )
        roles = [row[0] for row in result.fetchall()]

    print(f"You are about to remove user: {args.user}")
    if roles:
        print(f"Roles: {', '.join(roles)}")
    else:
        print("Roles: (none found)")
    confirm = input(f"Type the username '{args.user}' again to confirm: ").strip()
    if confirm != args.user:
        print("Aborted: username did not match.")
        return

    async with session_manager.raw_connection() as conn:
        # Drop owned objects and the user
        drop_owned_sql = f'DROP OWNED BY "{args.user}" CASCADE;'
        drop_user_sql = f'DROP USER IF EXISTS "{args.user}";'
        await conn.execute(drop_owned_sql)
        await conn.execute(drop_user_sql)

    await session_manager.close()
    print(f"Done - removed user `{args.user}`")


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
