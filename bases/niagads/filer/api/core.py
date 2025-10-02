from niagads.api.common.app.factory import AppFactory
from niagads.api.filer.documentation import OPEN_API_SPEC, APP_NAMESPACE
from niagads.api.filer.routes.root import router as RootRouter
from niagads.api.filer.routes.records.track import router as RecordRouter
from niagads.api.filer.routes.search import router as MetadataRouter
from niagads.api.filer.routes.data import router as DataRouter
from niagads.api.filer.routes.service import router as ServiceRouter
from niagads.api.filer.routes.records.collection import (
    router as CollectionRouter,
)
from niagads.api.filer.routes.dictionary import router as DictionaryRouter

# from niagads.api.filer.routes.qtls import router as QTLRouter

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
