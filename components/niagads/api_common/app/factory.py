from io import StringIO

from fastapi.openapi.utils import get_openapi
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute
from niagads.api_common.exception_handlers import (
    add_database_exception_handler,
    add_not_implemented_exception_handler,
    add_request_validation_exception_handler,
    add_runtime_exception_handler,
    add_system_exception_handler,
    add_validation_exception_handler,
)
from niagads.api_common.app.openapi import OpenAPISpec
from niagads.settings.core import ServiceEnvironment, get_service_environment
import yaml


class AppFactory:
    """Class that to creates and configures a FastAPI application
    for a NIAGADS Open Access API microservice."""

    def __init__(
        self,
        metadata: OpenAPISpec,
        env: str,
        namespace: str = "root",
        version: bool = False,
    ):
        """
        Initializes the AppFactory

        Args:
            metadata (OpenAPISpec): APP metadata
            env (str): production or development environment
            namespace (str, optional): for openapi specification x-namespace arg. Defaults to 'root'
            version (bool, optional): add API major  version to path.  Defaults to False
        """
        self.__app = None
        self.__metadata = metadata
        self.__version = f"/v{self.__metadata.version.split('.')[0]}"
        self.__namespace = namespace
        self.__create(version)
        self.__add_middleware()
        self.__add_exception_handlers()

    def get_version_prefix(self):
        return self.__version

    def get_app(self) -> FastAPI:
        """get the application object"""
        if self.__app is None:
            raise RuntimeError("Application is not initialized.")

        return self.__app

    def add_router(
        self,
        route: APIRoute,
        includeInSchema: bool = True,
        isDeprecated: bool = False,
        version: bool = False,
    ) -> None:
        """Add a route to the application"""
        if self.__app is None:
            raise RuntimeError("Application is not initialized.")

        self.__app.include_router(
            route,
            prefix=self.__version if version else "",
            include_in_schema=includeInSchema,
            deprecated=isDeprecated,
        )

    def __create(self, version: bool):
        """Creates the application"""

        prefix = self.__version if version else ""
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
            openapi_url=f"{prefix}/openapi.json",
            docs_url=f"{prefix}/docs",
            redoc_url=f"{prefix}/redoc",
            openapi_tags=[t.model_dump() for t in self.__metadata.openapi_tags],
            # responses=RESPONSES,
            generate_unique_id_function=self.__generate_unique_id,
        )

        self.__app.openapi = self.openapi

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

    def openapi(self):
        if self.__app.openapi_schema:
            return self.__app.openapi_schema

        openapi_schema = get_openapi(
            title=self.__app.title,
            version=self.__app.version,
            openapi_version=self.__app.openapi_version,
            summary=self.__app.summary,
            description=self.__app.description,
            terms_of_service=self.__app.terms_of_service,
            contact=self.__app.contact,
            license_info=self.__app.license_info,
            routes=self.__app.routes,
            webhooks=self.__app.webhooks.routes,
            tags=self.__app.openapi_tags,
            # if sub-api tacks on sub api path as a service URL, need to remove
            servers=[{"url": self.__metadata.service_url}],
            separate_input_output_schemas=self.__app.separate_input_output_schemas,
        )

        # flag beta route paths / updated by reference
        # update summary formatting
        paths: dict = openapi_schema["paths"]
        for path in paths.keys():
            for method in paths[path]:
                summary: str = paths[path][method]["summary"]
                if summary.endswith("-beta"):
                    summary = summary.replace("-beta", "")
                    paths[path][method].update(
                        {
                            "x-badges": [
                                {
                                    "name": "Beta",
                                    "position": "before",
                                    "color": "purple",
                                }
                            ]
                        }
                    )
                paths[path][method]["summary"] = (
                    summary.replace("-", " ")
                    .capitalize()
                    .replace(" api ", " API ")
                    .replace("bulk", "(Bulk)")
                )
        # openApiSchema["paths"] = paths
        openapi_schema["info"]["x-namespace"] = self.__namespace
        openapi_schema["info"]["x-major-version"] = self.__version

        # x-tagGroups
        if self.__metadata.xtag_groups is not None:
            openapi_schema["x-tagGroups"] = [
                tg.model_dump() for tg in self.__metadata.xtag_groups
            ]

        self.__app.openapi_schema = openapi_schema
        return self.__app.openapi_schema

    @staticmethod
    def __generate_unique_id(route: APIRoute):
        rName = route.name.lower().replace(" ", "_")
        if len(route.tags) > 1:
            rtag = route.tags[0].lower().replace(" ", "_").replace("'", "")
            return f"{rtag}-{rName}"
        else:
            return rName

    @staticmethod
    def get_openapi_yaml(app: FastAPI) -> str:
        """Get YAML-formatted openapi specification.

        Converts the API openapi JSON specification to yaml format and returns the formatted yaml

        adapted from https://github.com/tiangolo/fastapi/issues/1140#issuecomment-659469034
        """
        openapi_json = app.openapi()
        yaml_str = StringIO()
        yaml.dump(openapi_json, yaml_str, sort_keys=False)
        return yaml_str.getvalue()
