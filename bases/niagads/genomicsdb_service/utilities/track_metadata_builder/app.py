"""FastAPI + Jinja2 web utility for curator-friendly track metadata emission."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from niagads.genomics.sequence.assembly import Assembly

from .parsing import build_payload_from_form, to_error_map

APP_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(APP_DIR / "templates"))

app = FastAPI(title="Track Metadata Builder")


def _default_form_data() -> Dict[str, str]:
    return {
        "genome_build": Assembly.GRCh38.value,
    }


@app.get("/", response_class=HTMLResponse)
async def form_home(request: Request):
    return TEMPLATES.TemplateResponse(
        request=request,
        name="form.html",
        context={
            "form_data": _default_form_data(),
            "errors": {},
            "genome_build_options": Assembly.list(),
        },
    )


@app.post("/export")
async def export_metadata(request: Request):
    form = await request.form()
    raw_form = {k: (form.get(k) or "") for k in form.keys()}

    try:
        payload = build_payload_from_form(form)
    except ValidationError as err:
        return TEMPLATES.TemplateResponse(
            request=request,
            name="form.html",
            context={
                "form_data": raw_form,
                "errors": to_error_map(err),
                "genome_build_options": Assembly.list(),
            },
            status_code=422,
        )

    filename = f"track_metadata_{payload.track_id}.json"
    content = payload.model_dump(
        mode="json",
        exclude_none=True,
        exclude={"provenance": {"data_source_url"}},
    )

    return Response(
        content=json.dumps(content, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
