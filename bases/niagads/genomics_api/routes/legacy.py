from fastapi import APIRouter, Request, Response, Depends
from aiohttp import ClientSession
from niagads.requests.core import HttpClientSessionManager


router = APIRouter(
    prefix="/legacy",
)


# Shared client manager that creates a pooled ClientSession with base URL
LEGACY_CLIENT = HttpClientSessionManager(
    "https://www.niagads.org/genomics/service/", timeout=60
)


EXCLUDED_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
}


@router.get("/service/{path:path}")
async def legacy_service(
    path: str,
    request: Request,
    api_client_session: ClientSession = Depends(LEGACY_CLIENT),
) -> Response:
    endpoint = f"/{path}"

    async with api_client_session.get(endpoint, params=request.query_params) as resp:
        body = await resp.read()
        headers = {
            k: v for k, v in resp.headers.items() if k.lower() not in EXCLUDED_HEADERS
        }

        return Response(
            content=body,
            status_code=resp.status,
            headers=headers,
            media_type=resp.headers.get("content-type"),
        )
