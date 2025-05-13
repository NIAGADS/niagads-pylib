from typing import List

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from niagads.open_access_api_common.exception_handlers import (
    add_database_exception_handler,
    add_not_implemented_exception_handler,
    add_request_validation_exception_handler,
    add_runtime_exception_handler,
    add_system_exception_handler,
    add_validation_exception_handler,
)
from niagads.settings.core import ServiceEnvironment, get_service_environment
from pydantic import BaseModel


class OpenAPITag(BaseModel):
    name: str
    description: str
    externalDocs: dict[str, str]


class OpenAPISpec(BaseModel):
    title: str
    description: str
    summary: str
    version: str
    admin_email: str
    service_url: str
    openapi_tags: List[OpenAPITag]


class AppFactory:
    """Class that to creates and configures a FastAPI application
    for a NIAGADS Open Access API microservice."""

    def __init__(
        self,
        metadata: OpenAPISpec,
        env: str,
        routePath: str = "",
    ):
        """
        Initializes the AppFactory

        Args:
            metadata (OpenAPISpec): APP metadata
            env (str): production or development environment
        """
        self.__app = None
        self.__metadata = metadata
        self.__prefix = f"/v{self.__metadata.version.split('.')[0]}"  # {routePath}"

        self.__create()
        self.__add_middleware()
        self.__add_exception_handlers()

    def get_app(self) -> FastAPI:
        """get the application object"""
        if self.__app is None:
            raise RuntimeError("Application is not initialized.")

        return self.__app

    def add_router(
        self, route: APIRoute, includeInSchema: bool = True, isDeprecated: bool = False
    ) -> None:
        """Add a route to the application"""
        if self.__app is None:
            raise RuntimeError("Application is not initialized.")

        self.__app.include_router(
            route,
            prefix=self.__prefix,
            include_in_schema=includeInSchema,
            deprecated=isDeprecated,
        )

    def __create(self):
        """Creates the application"""
        self.__app = FastAPI(
            title=self.__metadata.title,
            description=self.__metadata.description,
            summary=self.__metadata.summary,
            version=self.__metadata.version,
            terms_of_service=f"{self.__metadata.service_url}/terms",
            contact={"name": "NIAGADS Support", "email": self.__metadata.admin_email},
            license_info={
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
            },
            servers=[{"url": self.__metadata.service_url}],
            swagger_ui_parameters={
                "apisSorter": "alpha",
                "operationsSorter": "alpha",
                "tagsSorter": "alpha",
            },
            openapi_url=f"{self.__prefix}/openapi.json",
            docs_url=f"{self.__prefix}/docs",
            redoc_url=f"{self.__prefix}/redoc",
            openapi_tags=[t.model_dump() for t in self.__metadata.openapi_tags],
        )

    def __add_middleware(self):
        """Adds middleware to the application"""

        if self.__app is None:
            raise RuntimeError("Application is not initialized")

        self.__app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID")

        serviceEnv: ServiceEnvironment = get_service_environment()

        self.__app.add_middleware(
            CORSMiddleware,
            # allow_origins=[Settings.from_env().API_PUBLIC_URL],
            allow_origins=(
                ["*"]
                if serviceEnv in [ServiceEnvironment.DEV, ServiceEnvironment.TEST]
                else []
            ),
            allow_origin_regex=r"https://.*\.niagads\.org",
            # allow_credentials=False,
            allow_methods=["GET"],
            # allow_headers=["*"] # probably don't need b/c there are default ones
        )

    def __add_exception_handlers(self):
        """Adds exception handlers to the application"""

        if self.__app is None:
            raise RuntimeError("Application is not initialized")
        add_runtime_exception_handler(self.__app)
        add_validation_exception_handler(self.__app)
        add_request_validation_exception_handler(self.__app)
        add_system_exception_handler(self.__app)
        add_database_exception_handler(self.__app)
        add_not_implemented_exception_handler(self.__app)
