import asyncio
from datetime import datetime
from typing import Optional

from niagads.common.core import ComponentBaseMixin
from niagads.database.ragdoc.schema import IngestionJob
from niagads.database.session import DatabaseSessionManager
from niagads.database.types import RetrievalStatus
from niagads.nlp.llm_types import LLM
from niagads.ragdoc.services.config import BaseRagdocServiceSettings
from niagads.ragdoc.services.ingestion import (
    DocumentIngestionRequest,
    DocumentIngestionService,
)
from niagads.ragdoc.services.jobs import IngestionJobService


class Settings(BaseRagdocServiceSettings):
    WORKER_POLL_INTERVAL: int = 5
    EMBEDDING_MODEL: Optional[str] = None


class DocumentIngestionWorker(ComponentBaseMixin):
    """Background worker that processes queued ingestion jobs."""

    def __init__(
        self,
        database_uri: str,
        embedding_model: str | None = None,
        poll_interval: int = 5,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        model = None if embedding_model is None else LLM(embedding_model)
        self._database_session_manager = DatabaseSessionManager(database_uri)
        self._ingestion_service = DocumentIngestionService(
            database_uri=database_uri,
            embedding_model=model,
            debug=debug,
            verbose=verbose,
        )
        self._job_service = IngestionJobService(
            database_uri=database_uri,
            debug=debug,
            verbose=verbose,
        )
        self._poll_interval = poll_interval

    async def process_job(self, job_id: int):
        """Process a single queued ingestion job and persist the outcome."""
        async with self._database_session_manager.session_ctx() as session:
            job = await session.get(IngestionJob, job_id)
            if job is None:
                raise ValueError(f"Ingestion job {job_id} not found")

            job.status = RetrievalStatus.IN_PROGRESS
            job.start_date = datetime.now()
            job.error_message = None
            await session.flush()
            await session.commit()

            url = job.url
            max_pages = job.max_pages

        try:
            result = await self._ingestion_service.ingest(
                DocumentIngestionRequest(url=url, max_pages=max_pages)
            )
        except Exception as err:
            async with self._database_session_manager.session_ctx() as session:
                job = await session.get(IngestionJob, job_id)
                job.status = RetrievalStatus.FAILED
                job.end_date = datetime.now()
                job.error_message = str(err)
                await session.flush()
                await session.commit()
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

    async def run(self):
        """Continuously poll for and process queued jobs."""
        try:
            while True:
                job_id = await self._job_service.fetch_next_pending_job_id()
                if job_id is None:
                    await asyncio.sleep(self._poll_interval)
                    continue

                try:
                    await self.process_job(job_id)
                except Exception:
                    self.logger.exception(f"Failed processing ingestion job {job_id}")
        finally:
            await self._ingestion_service.close()
            await self._job_service.close()
            await self._database_session_manager.close()


def main():
    """Run the ingestion worker."""
    settings = Settings.from_env()
    worker = DocumentIngestionWorker(
        database_uri=settings.DATABASE_URI,
        embedding_model=settings.EMBEDDING_MODEL,
        poll_interval=settings.WORKER_POLL_INTERVAL,
    )
    asyncio.run(worker.run())


if __name__ == "__main__":
    main()
