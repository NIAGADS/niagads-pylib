from io import StringIO

from niagads.api.common.app.types import AppMetadata
from niagads.api.common.config import Settings
import yaml
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute
from niagads.api.common.constants import RESPONSES
from niagads.api.common.exception_handlers import (
    add_database_exception_handler,
    add_not_implemented_exception_handler,
    add_request_validation_exception_handler,
    add_runtime_exception_handler,
    add_system_exception_handler,
)
from niagads.settings.core import ServiceEnvironment, get_service_environment
from starlette.types import Lifespan


class AppFactory:
    """Class that to creates and configures a FastAPI application
    for a NIAGADS Open Access API microservice."""

    def __init__(
        self,
        metadata: AppMetadata,
        env: str,
        lifespan: Lifespan[FastAPI] | None = None,
    ):
        """
        Initializes the AppFactory

        Args:
            metadata (OpenAPISpec): APP metadata
            env (str): production or development environment
            namespace (str, optional): for openapi specification x-namespace arg. Defaults to 'root'
            version (bool, optional): add API major  version to path.  Defaults to False
        """
        self._app: FastAPI = self._initialize_app(metadata, lifespan)
        self._add_middleware()
        self._add_exception_handlers()

    @property
    def app(self) -> FastAPI:
        """get the application object"""
        self._verify_app()
        return self._app

    def _verify_app(self):
        if not self._app:
            raise RuntimeError("Application is not initialized.")

    def _initialize_app(
        self,
        metadata: AppMetadata,
        lifespan: Lifespan[FastAPI] | None = None,
    ) -> FastAPI:
        """Creates the application"""

        return FastAPI(
            title=metadata.title,
            description=metadata.description,
            summary=metadata.summary,
            version=Settings.from_env().API_VERSION or "0.0.1",
            # terms_of_service= # FIXME: review and add terms of service
            contact={
                "name": "NIAGADS Support",
                "email": Settings.from_env().ADMIN_EMAIL,
            },
            license_info={
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
            },
            servers=metadata.servers,
            swagger_ui_parameters={
                "apisSorter": "alpha",
                "operationsSorter": "alpha",
                "tagsSorter": "alpha",
            },
            openapi_url=f"/openapi.json",
            docs_url=f"/docs",
            redoc_url=f"/redoc",
            lifespan=lifespan,
        )

    def _add_middleware(self):
        """Adds middleware to the application"""

        self._verify_app()

        self._app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")

        # FIXME: probably depends on service environment
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=(["*"]),
            allow_origin_regex=r"https://.*\.niagads\.org",
            allow_methods=["GET"],
        )

    def add_router(
        self,
        route: APIRoute,
        *,
        include_in_schema: bool = True,
        **kwargs,
    ) -> None:
        """Add a route to the application.  Takes any arguments allowed for
        FastAPI `include_router` see (https://fastapi.tiangolo.com/tutorial/bigger-applications/)
        """
        if self._app is None:
            raise RuntimeError("Application is not initialized.")

        self._app.include_router(route, include_in_schema=include_in_schema, **kwargs)

    def _add_exception_handlers(self):
        """Adds exception handlers to the application"""

        self._verify_app()
        add_runtime_exception_handler(self._app)
        add_request_validation_exception_handler(self._app)
        add_system_exception_handler(self._app)
        add_database_exception_handler(self._app)
        add_not_implemented_exception_handler(self._app)

    def get_openapi_yaml(self) -> str:
        """Get YAML-formatted openapi specification.

        Converts the API openapi JSON specification to yaml format and returns the formatted yaml

        adapted from https://github.com/tiangolo/fastapi/issues/1140#issuecomment-659469034
        """
        self._verify_app()
        openapi_json = self._app.openapi()
        yaml_str = StringIO()
        yaml.dump(openapi_json, yaml_str, sort_keys=False)
        return yaml_str.getvalue()
