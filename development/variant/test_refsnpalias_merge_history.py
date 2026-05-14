import asyncio

from sqlalchemy import select

from niagads.database.genomicsdb.schema.variant.mappings import RefSNPAlias
from niagads.database.session import DatabaseSessionManager
from niagads.settings.core import CustomSettings


class Settings(CustomSettings):
    DATABASE_URI: str


async def main():
    database_uri = Settings.from_env().DATABASE_URI
    session_manager = DatabaseSessionManager(database_uri)

    stmt = (
        select(
            RefSNPAlias.merge_history,
        )
        .where(RefSNPAlias.merge_history.is_not(None))
        .order_by(RefSNPAlias.ref_snp_alias_id)
        .limit(10)
    )

    try:
        async with session_manager.session_ctx() as session:
            result = await session.execute(stmt)
            rows = result.all()

        for row in rows:
            print(f"{row[0]}")
    finally:
        await session_manager.close()


asyncio.run(main())
