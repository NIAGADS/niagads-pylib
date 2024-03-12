from typing import Union
from fastapi import FastAPI

from .routers import filer

app = FastAPI(
        title="NIAGADS API",
        description="an application programming interface (API) that provides programmatic access to Open-Access resources at the NIA Genetics of Alzheimer's Disease Data Storage Site (NIAGADS)",
        summary="NIAGADS API",
        version="0.0.1",
        terms_of_service="http://example.com/terms/",
        contact={
            "name": "NIAGADS Support",
            "email": "help@niagads.org",
        },
        license_info={
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
        },
        root_path="/api"
    )

app.include_router(filer)

@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
async def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}