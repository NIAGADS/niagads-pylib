from datetime import datetime

from niagads.common.core import ComponentBaseMixin
from niagads.database.ragdoc.schema import IngestionJob
from niagads.database.session import DatabaseSessionManager
from niagads.database.types import RetrievalStatus
from niagads.ragdoc.services.ingestion import (
    DocumentIngestionRequest,
    DocumentIngestionService,
)
from sqlalchemy import Select, select


class IngestionJobService(ComponentBaseMixin):
    """Queue and process website ingestion jobs stored in the application database."""

    def __init__(
        self,
        database_uri: str,
        embedding_model=None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self._database_session_manager = DatabaseSessionManager(database_uri)
        self._database_uri = database_uri
        self._embedding_model = embedding_model

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

    async def process_job(self, job_id: int):
        """Process a single queued job and persist the outcome."""

        ingestion_service = DocumentIngestionService(
            database_uri=self._database_uri,
            embedding_model=self._embedding_model,
            debug=self._debug,
            verbose=self._verbose,
        )

        async with self._database_session_manager.session_ctx() as session:
            job = await session.get(IngestionJob, job_id)
            if job is None:
                raise ValueError(f"Ingestion job {job_id} not found")

            job.status = RetrievalStatus.IN_PROGRESS
            job.start_date = datetime.now()
            job.error_message = None
            await session.flush()
            await session.commit()

        try:
            result = await ingestion_service.ingest(
                DocumentIngestionRequest(url=job.url, max_pages=job.max_pages)
            )
        except Exception as err:
            async with self._database_session_manager.session_ctx() as session:
                job = await session.get(IngestionJob, job_id)
                job.status = RetrievalStatus.FAILED
                job.end_date = datetime.now()
                job.error_message = str(err)
                await session.flush()
                await session.commit()
            await ingestion_service.close()
            raise

        async with self._database_session_manager.session_ctx() as session:
            job = await session.get(IngestionJob, job_id)
            job.status = RetrievalStatus.SUCCESS
            job.end_date = datetime.now()
            job.num_documents = result.num_documents
            job.num_chunks = result.num_chunks
            job.num_embeddings = result.num_embeddings
            await session.flush()
            await session.commit()
        await ingestion_service.close()

    async def close(self):
        """Close DB/session resources held by the job service."""
        await self._database_session_manager.close()
