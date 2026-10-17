from fastapi import FastAPI
from niagads.api.common.app.factory import AppFactory
from niagads.api.common.app.types import AppMetadata
from niagads.api.common.config import Settings
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

# generate the app
app_factory = AppFactory(metadata=metadata, env=get_service_environment())
