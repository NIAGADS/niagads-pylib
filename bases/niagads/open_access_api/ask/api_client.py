"""Fixed API operations only; no database queries or arbitrary upstream URLs."""

import json
import logging
from urllib.parse import quote

import httpx
from niagads.api.common.types import AnnotationKind
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
    if definition.annotation == AnnotationKind.ASSOCIATIONS:
        params["content"] = definition.response_config.content.value
    identifier = definition.entity.value
    if f"{{{identifier}}}" in path:
        value = sanitize(params.pop(identifier))
        if definition.entity == Entity.GENE:
            value = GenomicFeature.validate_gene_id(value)
        elif definition.entity == Entity.VARIANT:
            value = GenomicFeature.validate_variant_id(value)
        if not value or value in {".", ".."} or "/" in value:
            raise ValueError("Invalid record identifier")
        path = path.format(**{identifier: quote(value, safe="")})
    chunks = []
    size = 0
    async with client.stream("GET", path, params=params) as response:
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > 1_048_576:
                raise ValueError(
                    "API response exceeded prototype size limit; narrow the query"
                )
            chunks.append(chunk)
        body = b"".join(chunks)
        if response.is_error:
            logging.getLogger(__name__).error(
                "ASK API retrieval failed: operation=%s HTTP %s response=%s",
                operation,
                response.status_code,
                body.decode("utf-8", errors="replace"),
            )
        if response.status_code == 501:
            raise NotImplementedError(
                "API operation awaits local ORM/retrieval integration"
            )
        response.raise_for_status()
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
                raise ValueError("API returned a semantic match without an identifier")
            row["id"] = row["matched_record_id"]
            row.update(row.get("matched_record_details") or {})
        rows.append(row)
    pagination = payload.get("pagination") or {}
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
