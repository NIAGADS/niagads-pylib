"""Fixed API operations only; no database queries or arbitrary upstream URLs."""

import asyncio
import json
from urllib.parse import quote

import httpx
from niagads.api.common.types import AnnotationKind, ResponseFormat
from niagads.api.common.utils import sanitize
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.search.models.record import SearchMatch
from niagads.common.types import Entity
from niagads.open_access_api.ask.contracts import ResultSet
from niagads.open_access_api.ask.operations import OPERATIONS


async def retrieve(
    client: httpx.AsyncClient, operation: str, parameters: dict
) -> ResultSet:
    """Execute a registered API GET and retain a bounded authoritative page."""
    if operation not in OPERATIONS:
        raise ValueError("Operation is not registered")
    definition = OPERATIONS[operation]
    path = definition.endpoint
    semantic_search = definition.response_config.record_model is SearchMatch
    params = dict(parameters)
    params["format"] = ResponseFormat.JSON.value
    if definition.annotation == AnnotationKind.ASSOCIATIONS:
        params["content"] = definition.response_config.content.value
    identifier = definition.entity.value
    try:
        if f"{{{identifier}}}" in path:
            value = sanitize(params.pop(identifier))
            if definition.entity == Entity.GENE:
                value = GenomicFeature.validate_gene_id(value)
            elif definition.entity == Entity.VARIANT:
                value = GenomicFeature.validate_variant_id(value)
            if not value or value in {".", ".."} or "/" in value:
                raise ValueError("Invalid record identifier")
            path = path.format(**{identifier: quote(value, safe="")})
    except ValueError as exc:
        raise RuntimeError(f"Invalid input for {operation}: {exc}") from exc
    chunks = []
    size = 0
    try:
        async with asyncio.timeout(client.timeout.read):
            async with client.stream("GET", path, params=params) as response:
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 1_048_576:
                        raise RuntimeError(
                            f"API response for {operation} exceeded 1 MiB."
                        )
                    chunks.append(chunk)
                body = b"".join(chunks)
                if response.status_code == 404:
                    payload = {"data": []}
                else:
                    if response.is_error:
                        raise RuntimeError(
                            f"API request for {operation} failed "
                            f"(HTTP {response.status_code}): "
                            f"{body.decode('utf-8', errors='replace')}"
                        )
                    payload = json.loads(body)
                    if "data" not in payload:
                        raise RuntimeError(
                            f"API response for {operation} has no data: {payload!r}"
                        )
        data = payload["data"]
        rows = []
        for record in data[:50]:
            row = dict(record)
            if semantic_search:
                row.update(row.get("matched_record_details") or {})
            rows.append(row)
        pagination = payload.get("pagination") or {}
        if not isinstance(pagination, dict):
            raise ValueError("API returned invalid pagination metadata")
        page = int(params.get("page", 1))
        has_more = len(data) > 50 or pagination.get("total_pages", page) > page
        return ResultSet(
            entity=definition.entity,
            annotation=definition.annotation,
            content=definition.response_config.content,
            rows=rows,
            page=page,
            limit=50,
            has_more=has_more,
            parameters=parameters,
            sources=list(
                dict.fromkeys(
                    str(row.get("track") or row.get("id") or row.get("source_id"))
                    for row in rows
                    if row.get("track") or row.get("id") or row.get("source_id")
                )
            ),
            warnings=(
                ["Ranked semantic results are candidates and are not exhaustive."]
                if semantic_search
                else []
            )
            + (
                ["Only the first 50 records of this API page are shown."]
                if len(data) > 50
                else []
            ),
        )
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"API retrieval for {operation} failed: {type(exc).__name__}: {exc}"
        ) from exc
