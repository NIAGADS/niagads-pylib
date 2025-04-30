from niagads.open_access_api_common.app import AppFactory
from niagads.open_access_api_common.config.core import get_service_environment
from niagads.open_access_filer_api.documentation import OPEN_API_SPEC
from niagads.open_access_filer_api.routes.root import router as InfoRouter
import uvicorn

# generate the app
appFactory = AppFactory(
    routePath="filer", metadata=OPEN_API_SPEC, env=get_service_environment()
)

# add the child routes
appFactory.add_router(InfoRouter)
"""
app.include_router(TrackRouter)
app.include_router(MetadataRouter)
app.include_router(DataRouter)
app.include_router(ServiceRouter)
app.include_router(CollectionRouter)
app.include_router(QTLRouter)
"""

# get the application object
app = appFactory.get_app()


if __name__ == "__main__":
    uvicorn.run(app="app:app")
