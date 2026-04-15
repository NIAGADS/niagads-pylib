import asyncio
from typing import Optional

from niagads.common.core import ComponentBaseMixin
from niagads.nlp.llm_types import LLM
from niagads.settings.core import CustomSettings
from niagads.utils.regular_expressions import RegularExpressions
from pydantic import Field

from development.chatbot_poc.services.jobs import IngestionJobService


class Settings(CustomSettings):
    DATABASE_URI: str = Field(..., pattern=RegularExpressions.POSTGRES_URI)
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
        self._job_service = IngestionJobService(
            database_uri=database_uri,
            embedding_model=model,
            debug=debug,
            verbose=verbose,
        )
        self._poll_interval = poll_interval

    async def run(self):
        """Continuously poll for and process queued jobs."""
        try:
            while True:
                job_id = await self._job_service.fetch_next_pending_job_id()
                if job_id is None:
                    await asyncio.sleep(self._poll_interval)
                    continue

                try:
                    await self._job_service.process_job(job_id)
                except Exception:
                    self.logger.exception(f"Failed processing ingestion job {job_id}")
        finally:
            await self._job_service.close()


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
