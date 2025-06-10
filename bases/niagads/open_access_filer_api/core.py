from niagads.open_access_api_common.app import AppFactory
from niagads.open_access_filer_api.documentation import OPEN_API_SPEC, APP_NAMESPACE
from niagads.open_access_filer_api.routes.root import router as RootRouter
from niagads.open_access_filer_api.routes.record import router as RecordRouter
from niagads.open_access_filer_api.routes.metadata import router as MetadataRouter
from niagads.open_access_filer_api.routes.data import router as DataRouter
from niagads.open_access_filer_api.routes.service import router as ServiceRouter
from niagads.open_access_filer_api.routes.collection import router as CollectionRouter

# from niagads.open_access_filer_api.routes.qtls import router as QTLRouter

from niagads.settings.core import get_service_environment
import uvicorn

# generate the app
appFactory = AppFactory(
    metadata=OPEN_API_SPEC, env=get_service_environment(), namespace=APP_NAMESPACE
)

# add the child routes
appFactory.add_router(RootRouter)
appFactory.add_router(RecordRouter)
appFactory.add_router(MetadataRouter)
appFactory.add_router(DataRouter)
appFactory.add_router(CollectionRouter)
appFactory.add_router(ServiceRouter)

# appFactory.add_router(QTLRouter)

# get the application object
app = appFactory.get_app()


if __name__ == "__main__":
    uvicorn.run(app="app:app")
