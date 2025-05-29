from copy import deepcopy
from typing import Any, Dict, List
from fastapi import FastAPI
from niagads.open_access_api_common.config.constants import SharedOpenAPIxGroupTags
import uvicorn
from niagads.open_access_api.documentation import OPEN_API_SPEC
from niagads.open_access_api.routes.root import router as RootRouter
from niagads.open_access_api_common.app import AppFactory
from niagads.open_access_filer_api.core import app as FILERApp  # Import the FILER app
from niagads.open_access_genomics_api.core import app as GenomicsApp
from niagads.settings.core import get_service_environment


def custom_openapi(factory: AppFactory, subAPIs=List[FastAPI]):
    # get root openapi
    specification: Dict[str, Any] = factory.openapi()
    specification.update({"components": {"schemas": {}}})

    # fetch the openapi specification for each sub-api
    api: FastAPI  # typehint
    for api in subAPIs:
        apiSpec: Dict[str, Any] = api.openapi()

        # prefix routes
        routePrefix: str = (
            f"{factory.get_version_prefix()}/{apiSpec['info']['x-namespace']}"
        )
        routes = {f"{routePrefix}{k}": v for k, v in apiSpec["paths"].items()}
        specification["paths"].update(routes)

        # extract and concatenate schemas
        if "components" in apiSpec:
            specification["components"]["schemas"].update(
                apiSpec["components"]["schemas"]
            )

    # x-tagGroups
    specification["x-tagGroups"] = [tg.serialize() for tg in SharedOpenAPIxGroupTags]

    return specification


# generate the app
appFactory = AppFactory(
    metadata=OPEN_API_SPEC, env=get_service_environment(), version=True
)

appFactory.add_router(RootRouter, version=True)

# get the application object
app = appFactory.get_app()

app.mount(f"{appFactory.get_version_prefix()}/filer", FILERApp)
app.mount(f"{appFactory.get_version_prefix()}/genomics", GenomicsApp)

app.openapi_schema = custom_openapi(appFactory, [GenomicsApp, FILERApp])

if __name__ == "__main__":
    uvicorn.run(app="app:app")
