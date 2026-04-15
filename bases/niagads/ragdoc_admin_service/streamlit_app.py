import asyncio
from typing import Optional

import pandas as pd
import streamlit as st
from niagads.common.core import ComponentBaseMixin
from niagads.database.types import RetrievalStatus
from niagads.ragdoc.services.jobs import IngestionJobService
from niagads.settings.core import CustomSettings
from niagads.utils.regular_expressions import RegularExpressions
from pydantic import Field


class Settings(CustomSettings):
    DATABASE_URI: Optional[str] = Field(None, pattern=RegularExpressions.POSTGRES_URI)


class RAGDocAdminApp(ComponentBaseMixin):
    """Streamlit application for queuing and monitoring RAG document jobs."""

    def __init__(
        self,
        database_uri: str | None = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self.__database_uri = (
            Settings.from_env().DATABASE_URI if database_uri is None else database_uri
        )

    def run(self):
        """Render and run the Streamlit application."""
        st.set_page_config(page_title="RAG Document Admin", layout="centered")
        st.title("RAG Document Admin")
        st.caption("Queue website crawls and monitor processing status.")

        with st.form("add_url_form"):
            url = st.text_input("Root URL")
            max_pages_value = st.number_input(
                "Max Pages",
                min_value=1,
                value=25,
                step=1,
                help="Optional per-run crawl limit.",
            )
            add_url = st.form_submit_button("Add URL")

        if add_url:
            self.__create_job(url=url, max_pages=int(max_pages_value))

        if st.button("Refresh Status"):
            st.rerun()

        jobs = self.__list_jobs()
        if jobs:
            self.__render_progress(jobs)
            st.subheader("Ingestion Jobs")
            st.dataframe(pd.DataFrame(jobs), use_container_width=True)

    def __create_job(self, url: str, max_pages: int):
        """Create a queued ingestion job."""
        normalized_url = url.strip()
        if not normalized_url:
            st.error("Root URL is required.")
            return

        asyncio.run(self.__create_job_async(normalized_url, max_pages))
        st.success(f"Queued {normalized_url}")

    async def __create_job_async(self, url: str, max_pages: int):
        """Async helper to create a queued ingestion job."""
        service = IngestionJobService(database_uri=self.__database_uri)
        try:
            await service.create_job(url=url, max_pages=max_pages)
        finally:
            await service.close()

    def __list_jobs(self) -> list[dict]:
        """Return job status rows for UI rendering."""
        return asyncio.run(self.__list_jobs_async())

    async def __list_jobs_async(self) -> list[dict]:
        """Async helper to load ingestion jobs from the database."""
        service = IngestionJobService(database_uri=self.__database_uri)
        try:
            jobs = await service.list_jobs()
        finally:
            await service.close()

        return [
            {
                "job_id": job.ingestion_job_id,
                "url": job.url,
                "status": job.status,
                "max_pages": job.max_pages,
                "num_documents": job.num_documents,
                "num_chunks": job.num_chunks,
                "num_embeddings": job.num_embeddings,
                "error": job.error_message,
                "created": job.creation_date,
                "started": job.start_date,
                "ended": job.end_date,
            }
            for job in jobs
        ]

    def __render_progress(self, jobs: list[dict]):
        """Render overall ingestion progress for queued and completed jobs."""
        total = len(jobs)
        completed = len(
            [
                job
                for job in jobs
                if job["status"] in (RetrievalStatus.SUCCESS, RetrievalStatus.FAILED)
            ]
        )
        st.progress(
            0.0 if total == 0 else completed / total,
            text=f"{completed} of {total} jobs completed",
        )


def main():
    """Run the RAG document Streamlit admin application."""
    app = RAGDocAdminApp()
    app.run()


if __name__ == "__main__":
    main()
