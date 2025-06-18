import uvicorn
from niagads.open_access_api_common.app.factory import AppFactory
from niagads.open_access_genomics_api.documentation import APP_NAMESPACE, OPEN_API_SPEC
from niagads.open_access_genomics_api.routes.collection import (
    router as CollectionRouter,
)
from niagads.open_access_genomics_api.routes.root import router as RootRouter
from niagads.open_access_genomics_api.routes.service import router as ServiceRouter
from niagads.open_access_genomics_api.routes.track import router as TrackRouter
from niagads.settings.core import get_service_environment


# generate the app
appFactory = AppFactory(
    metadata=OPEN_API_SPEC, env=get_service_environment(), namespace=APP_NAMESPACE
)

# add the child routes
appFactory.add_router(RootRouter)
# appFactory.add_router(TrackRouter)
# appFactory.add_router(CollectionRouter)
appFactory.add_router(ServiceRouter)

# get the application object
app = appFactory.get_app()


if __name__ == "__main__":
    uvicorn.run(app="app:app")
