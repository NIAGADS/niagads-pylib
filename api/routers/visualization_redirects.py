from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import json
from api.dependencies.exceptions import RESPONSES

ENDPOINT='http://localhost:3000/table'

router = APIRouter(
    # include_in_schema = False,
    prefix='/view',
    tags=['Visualizations'],
    responses=RESPONSES,
)

@router.get("/table")
async def table(request: Request, requestId: str, field: str):
    data = request.session[requestId + '_' + field]
    request = ENDPOINT + '?data=' + json.dumps(data)
    return RedirectResponse(url=request)
