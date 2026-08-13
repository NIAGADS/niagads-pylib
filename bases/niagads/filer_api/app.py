import uvicorn
from niagads.api.common.app.factory import AppFactory
from niagads.filer_api.documentation import APP_NAMESPACE, OPEN_API_SPEC
from niagads.filer_api.routes.records.track import router as TrackRecordRouter
from niagads.filer_api.routes.root import router as StatusRouter
from niagads.settings.core import get_service_environment

# generate the app
app_factory = AppFactory(
    metadata=OPEN_API_SPEC, env=get_service_environment(), namespace=APP_NAMESPACE
)

# add the child routes
app_factory.add_router(StatusRouter)
app_factory.add_router(TrackRecordRouter)


# app_factory.add_router(QTLRouter)

# get the application object
app = app_factory.get_app()


if __name__ == "__main__":
    uvicorn.run(app="app:app")
