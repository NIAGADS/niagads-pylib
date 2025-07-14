from copy import deepcopy
import json
from typing import Any, Dict, List, Set

import uvicorn
from fastapi import FastAPI
from niagads.open_access_api.documentation import OPEN_API_SPEC
from niagads.open_access_api.routes.root import router as RootRouter
from niagads.api_common.app.factory import AppFactory
from niagads.filer_api.core import app as FILERApp  # Import the FILER app
from niagads.genomics_api.core import app as GenomicsApp
from niagads.settings.core import get_service_environment
from niagads.api_common.config import Settings


def _openapi_update_xtag_groups(xTagGroups: List[dict]):
    # find and combine duplicates
    uniqueXTags = {}
    for tagGroup in xTagGroups:
        if tagGroup["name"] not in uniqueXTags:
            uniqueXTags[tagGroup["name"]] = tagGroup
        else:
            uniqueXTags[tagGroup["name"]]["tags"].extend(tagGroup["tags"])

    return list(uniqueXTags.values())


def _openapi_update_routes(
    routes: dict, traitTagRef: List[str], namespace: str, version: str = None
):
    """
    update all route paths:
    1. prefix paths with version and subapi namespace (lower)
    2. prefix tags with "namespace: "

    Args:
        routes (dict): the openapi route spec
        traitTagRef (list): trait tags; don't need to be prefixed
        version (str): api major version
        namespace (str): route namespace
    """
    # route structure: { <path> : {<method, e.g., get>: props}}

    # all endpoints should only have one 'get' method, but iterating
    # to cover future scenarios
    updatedRoutes = {}
    for path, route in routes.items():
        updatedPath: str = (
            f"{version}/{namespace.lower()}{path}"
            if version is not None
            else f"/{namespace.lower()}{path}"
        )

        route: dict
        for method, props in route.items():
            updatedRoutes.update({updatedPath: {method: deepcopy(props)}})
            summary = updatedRoutes[updatedPath][method]["summary"]
            updatedRoutes[updatedPath][method]["summary"] = f"{namespace}: {summary}"

    return updatedRoutes


def custom_openapi(factory: AppFactory, subAPIs=List[FastAPI], version: bool = False):
    # get root openapi
    specification: Dict[str, Any] = factory.openapi()
    specification.update({"components": {"schemas": {}}})

    # gather tags and tag groups as unqiue sets
    tagSet: Set = set([json.dumps(t) for t in specification["tags"]])
    tagGroupSet: Set = set([json.dumps(tg) for tg in specification["x-tagGroups"]])

    traitOnlyTags = []

    # fetch the openapi specification for each sub-api
    api: FastAPI  # typehint
    for api in subAPIs:
        apiSpec: Dict[str, Any] = api.openapi()
        namespace: str = apiSpec["info"]["x-namespace"]

        # extract and add tags to the specification; use set to ensure uniqueness
        # prefix tags by namespace to make unique and ensure relative anchors are
        # also extract / flag trait-only tags; do not prefix those
        # generated correctly

        t: dict
        for t in apiSpec["tags"]:
            if t.get("x-traitTag", False):
                traitOnlyTags.append(t["name"])
            # else:
            #     t["name"] = f"{namespace}-{t['name']}"
            #     t["x-displayName"] = f"{namespace}: {t['x-displayName']}"
            tagSet.add(json.dumps(t))

        # tagSet.update([json.dumps(t) for t in apiSpec["tags"]])

        # prefix route paths and tags
        routes = _openapi_update_routes(
            dict(apiSpec["paths"].items()),
            traitOnlyTags,
            namespace,
            factory.get_version_prefix() if version else None,
        )
        specification["paths"].update(routes)

        # ditto for tag groups, but do null check
        if "x-tagGroups" in apiSpec:
            for tg in apiSpec["x-tagGroups"]:
                # tg["tags"] = [f"{namespace}-{t}" for t in tg["tags"]]
                tagGroupSet.add(json.dumps(tg))

        # extract and concatenate schemas
        if "components" in apiSpec:
            specification["components"]["schemas"].update(
                apiSpec["components"]["schemas"]
            )

    # update x-tagGroups
    uniqueXTagGroups = sorted(
        [json.loads(tg) for tg in tagGroupSet], key=lambda d: d["x-sortOrder"]
    )
    specification["x-tagGroups"] = _openapi_update_xtag_groups(uniqueXTagGroups)

    # update tags and sort
    specification["tags"] = sorted(
        [json.loads(t) for t in tagSet], key=lambda d: d["x-sortOrder"]
    )

    return specification


# generate the app
useVersioning = not Settings.from_env().LTS
app_factory = AppFactory(
    metadata=OPEN_API_SPEC, env=get_service_environment(), version=useVersioning
)

app_factory.add_router(RootRouter, version=useVersioning)

# get the application object
app = app_factory.get_app()


app.mount(
    f"{app_factory.get_version_prefix() if useVersioning else ""}/filer", FILERApp
)
app.mount(
    f"{app_factory.get_version_prefix() if useVersioning else ""}/genomics", GenomicsApp
)

app.openapi_schema = custom_openapi(app_factory, [GenomicsApp, FILERApp], useVersioning)

if __name__ == "__main__":
    uvicorn.run(app="app:app")
