from niagads.common.core import ComponentBaseMixin
from niagads.database.ragdoc.schema import IngestionJob
from niagads.database.session import DatabaseSessionManager
from niagads.database.types import RetrievalStatus
from sqlalchemy import Select, select


class IngestionJobService(ComponentBaseMixin):
    """Queue and inspect website ingestion jobs stored in the application database."""

    def __init__(
        self,
        database_uri: str,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self._database_session_manager = DatabaseSessionManager(database_uri)

    async def create_job(self, url: str, max_pages: int | None = None) -> int:
        """Insert a pending ingestion job and return its primary key."""
        async with self._database_session_manager.session_ctx() as session:
            job = IngestionJob(
                url=url,
                max_pages=max_pages,
                status=RetrievalStatus.PENDING,
            )
            session.add(job)
            await session.flush()
            await session.commit()
            return job.ingestion_job_id

    async def list_jobs(self) -> list[IngestionJob]:
        """Return queued and completed jobs ordered newest first."""
        async with self._database_session_manager.session_ctx() as session:
            statement: Select = select(IngestionJob).order_by(
                IngestionJob.creation_date.desc()
            )
            result = await session.execute(statement)
            return list(result.scalars().all())

    async def fetch_next_pending_job_id(self) -> int | None:
        """Fetch the primary key of the next pending ingestion job."""
        async with self._database_session_manager.session_ctx() as session:
            statement: Select = (
                select(IngestionJob)
                .where(IngestionJob.status == RetrievalStatus.PENDING)
                .order_by(IngestionJob.creation_date.asc())
                .limit(1)
            )
            result = await session.execute(statement)
            job = result.scalar_one_or_none()
            if job is None:
                return None
            return job.ingestion_job_id

    async def close(self):
        """Close DB/session resources held by the job service."""
        await self._database_session_manager.close()
