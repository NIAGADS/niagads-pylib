from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from niagads.api.common.app.factory import AppFactory
from niagads.api.common.app.types import AppMetadata
from niagads.database.genomicsdb.intervals import fetch_bin_index_reference
from niagads.open_access_api.dependencies import OpenAccessEndpointContext
from niagads.open_access_api.routes.records.gene import router as GeneRecordRouter
from niagads.settings.core import get_service_environment

metadata = AppMetadata(
    title="NIAGADS Open Access API",
    description=(
        "The NIAGADS Open Access API provides programmatic access "
        "to publicly available Alzheimer's disease and related dementias (AD/ADRD) "
        "genomic data, annotations, and research resources. It supports querying "
        "genetic variants, genes, GWAS summary statistics, genetic associations, "
        "functional annotations, and related datasets across NIAGADS Open "
        "Access resources."
    ),
    summary=(
        "NIAGADS Open Access API for Alzheimer's disease and related dementias "
        "genomic data and annotations."
    ),
    servers=[{"url": "https://api.niagads.org", "description": "Production server"}],
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize the shared interval-bin reference before serving requests.

    Args:
        app (FastAPI): Application whose state holds the interval-bin reference.

    Yields:
        None: Control while the application serves requests.
    """
    await OpenAccessEndpointContext.verify_database_connection()
    database_dependency = (
        OpenAccessEndpointContext.model_fields["database_session"]
        .metadata[0]
        .dependency
    )
    async with database_dependency.session_ctx() as session:
        app.state.bin_index_reference = await fetch_bin_index_reference(session)
    yield


# generate the app
app_factory = AppFactory(
    metadata=metadata,
    env=get_service_environment(),
    lifespan=lifespan,
)
app_factory.add_router(GeneRecordRouter)

# get the application object
app = app_factory.app

if __name__ == "__main__":
    uvicorn.run(app="app:app")
