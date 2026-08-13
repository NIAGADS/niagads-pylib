import uvicorn
from niagads.api.common.app.factory import AppFactory
from niagads.api.genomicsdb.documentation import APP_NAMESPACE, OPEN_API_SPEC
from niagads.api.genomicsdb.routes.records.collection import (
    router as CollectionRouter,
)
from niagads.api.genomicsdb.routes.root import router as RootRouter
from niagads.api.genomicsdb.routes.service.basic import router as ServiceRouter
from niagads.api.genomicsdb.routes.records.track import router as TrackRouter
from niagads.api.genomicsdb.routes.records.gene import router as GeneRouter
from niagads.api.genomicsdb.routes.records.region import router as RegionRouter
from niagads.api.genomicsdb.routes.search import router as SearchRouter
from niagads.api.genomicsdb.routes.records.variant import (
    router as VariantRouter,
)
from niagads.api.genomicsdb.routes.service.igvbrowser.service import (
    router as IGVServiceRouter,
)
from niagads.api.genomicsdb.routes.service.igvbrowser.track.variant import (
    router as IGVVariantTrackRouter,
)

from niagads.settings.core import get_service_environment


# generate the app
app_factory = AppFactory(
    metadata=OPEN_API_SPEC, env=get_service_environment(), namespace=APP_NAMESPACE
)

# add the child routes
app_factory.add_router(RootRouter)
app_factory.add_router(GeneRouter)
app_factory.add_router(VariantRouter)
app_factory.add_router(RegionRouter)
# app_factory.add_router(TrackRouter)
# app_factory.add_router(CollectionRouter)

# app_factory.add_router(SearchRouter)
app_factory.add_router(ServiceRouter)

# app_factory.add_router(IGVServiceRouter)
# app_factory.add_router(IGVVariantTrackRouter)

# get the application object
app = app_factory.get_app()


if __name__ == "__main__":
    uvicorn.run(app="app:app")
