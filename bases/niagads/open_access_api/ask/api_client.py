"""Fixed API operations only; no database queries or arbitrary upstream URLs."""

import asyncio
import json
from urllib.parse import quote

import httpx
from niagads.api.common.exception_handlers import handled_request_exception
from niagads.api.common.services.embeddings import QueryEmbeddingError
from niagads.api.common.types import AnnotationKind
from niagads.api.common.utils import sanitize
from niagads.common.genomic.features.models import GenomicFeature
from niagads.common.search.models.record import SearchMatch
from niagads.common.types import Entity
from niagads.open_access_api.ask.contracts import AskErrorCode, ResultSet
from niagads.open_access_api.ask.errors import (
    RetrievalError,
    issue_for_exception,
    issue_for_status,
    make_issue,
)
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
        raise RetrievalError(make_issue(AskErrorCode.INVALID_INPUT, operation)) from exc
    chunks = []
    size = 0
    context = {}
    token = handled_request_exception.set(context)
    request_id = client.headers.get("x-request-id")
    try:
        async with asyncio.timeout(client.timeout.read):
            async with client.stream("GET", path, params=params) as response:
                request_id = response.headers.get("x-request-id") or request_id
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    original = context.get("exception")
                    issue = (
                        issue_for_exception(original, operation, request_id)
                        if isinstance(original, QueryEmbeddingError)
                        else issue_for_status(
                            response.status_code, operation, request_id
                        )
                    )
                    raise RetrievalError(issue, response.status_code) from (
                        original or exc
                    )
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > 1_048_576:
                        raise RetrievalError(
                            make_issue(
                                AskErrorCode.RESPONSE_TOO_LARGE, operation, request_id
                            )
                        )
                    chunks.append(chunk)
                body = b"".join(chunks)
    except RetrievalError:
        raise
    except Exception as exc:
        raise RetrievalError(issue_for_exception(exc, operation, request_id)) from exc
    finally:
        handled_request_exception.reset(token)
    try:
        payload = json.loads(body)
        if not isinstance(payload, dict) or "data" not in payload:
            raise ValueError("API returned an unsupported record envelope")
        data = payload["data"]
        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise ValueError("API returned an unsupported record shape")
        rows = []
        for record in data[:50]:
            row = dict(record)
            if semantic_search:
                if "matched_record_id" not in row:
                    raise ValueError(
                        "API returned a semantic match without an identifier"
                    )
                row["id"] = row["matched_record_id"]
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
    except (ValueError, TypeError, KeyError) as exc:
        raise RetrievalError(
            make_issue(AskErrorCode.MALFORMED_RESPONSE, operation, request_id)
        ) from exc
