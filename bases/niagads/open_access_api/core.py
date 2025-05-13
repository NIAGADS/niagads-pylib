import uvicorn
from niagads.open_access_api.documentation import OPEN_API_SPEC
from niagads.open_access_api.routes.root import router as RootRouter
from niagads.open_access_api_common.app import AppFactory
from niagads.open_access_filer_api.core import app as FILERApp  # Import the FILER app
from niagads.open_access_genomics_api.core import app as GenomicsApp
from niagads.settings.core import get_service_environment

# generate the app
appFactory = AppFactory(metadata=OPEN_API_SPEC, env=get_service_environment())

appFactory.add_router(RootRouter)

# get the application object
app = appFactory.get_app()

app.mount("/filer", FILERApp)
app.mount("/genomics", GenomicsApp)


if __name__ == "__main__":
    uvicorn.run(app="app:app")
