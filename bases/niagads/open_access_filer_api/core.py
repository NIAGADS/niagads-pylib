from niagads.open_access_api_common.app.factory import AppFactory
from niagads.open_access_filer_api.documentation import OPEN_API_SPEC, APP_NAMESPACE
from niagads.open_access_filer_api.routes.root import router as RootRouter
from niagads.open_access_filer_api.routes.records.track import router as RecordRouter
from niagads.open_access_filer_api.routes.search import router as MetadataRouter
from niagads.open_access_filer_api.routes.data import router as DataRouter
from niagads.open_access_filer_api.routes.service import router as ServiceRouter
from niagads.open_access_filer_api.routes.records.collection import (
    router as CollectionRouter,
)
from niagads.open_access_filer_api.routes.dictionary import router as DictionaryRouter

# from niagads.open_access_filer_api.routes.qtls import router as QTLRouter

from niagads.settings.core import get_service_environment
import uvicorn

# generate the app
app_factory = AppFactory(
    metadata=OPEN_API_SPEC, env=get_service_environment(), namespace=APP_NAMESPACE
)

# add the child routes
app_factory.add_router(RootRouter)
app_factory.add_router(RecordRouter)
app_factory.add_router(MetadataRouter)
app_factory.add_router(DataRouter)
# app_factory.add_router(CollectionRouter)
app_factory.add_router(ServiceRouter)
app_factory.add_router(DictionaryRouter)

# app_factory.add_router(QTLRouter)

# get the application object
app = app_factory.get_app()


if __name__ == "__main__":
    uvicorn.run(app="app:app")
