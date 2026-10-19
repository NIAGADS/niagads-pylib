"""Fixed API operations only; no database queries or arbitrary upstream URLs."""

import json
from urllib.parse import quote

import httpx
from niagads.common.genomic.features.models import GenomicFeature
from niagads.open_access_api.ask.contracts import ResultSet

OPERATIONS = {
    "search_tracks": ("/query/tracks", "tracks"),
    "search_genes": ("/query/genes", "genes"),
    "gene": ("/record/gene/{gene}", "genes"),
    "gene_structure": ("/record/gene/{gene}/structure", "structure"),
    "gene_associations": ("/record/gene/{gene}/associations", "associations"),
    "region_associations": ("/record/region/associations", "associations"),
}


async def retrieve(
    client: httpx.AsyncClient, operation: str, parameters: dict
) -> ResultSet:
    """Execute a registered API GET and retain a bounded authoritative page."""
    if operation not in OPERATIONS:
        raise ValueError("Operation is not registered")
    path, kind = OPERATIONS[operation]
    params = dict(parameters)
    if "{gene}" in path:
        gene = params.pop("gene")
        GenomicFeature.validate_gene_id(gene)
        path = path.format(gene=quote(gene, safe=""))
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
        if response.status_code == 501:
            raise NotImplementedError(
                "API operation awaits local ORM/retrieval integration"
            )
        response.raise_for_status()
    payload = json.loads(body)
    if not isinstance(payload, dict) or "data" not in payload:
        raise ValueError("API returned an unsupported record envelope")
    data = payload["data"]
    if isinstance(data, dict):
        if kind == "structure":
            data = [data] if data else []
        else:
            data = [
                row
                for values in data.values()
                for row in (values if isinstance(values, list) else [values])
            ]
    if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
        raise ValueError("API returned an unsupported record shape")
    rows = []
    for raw in data[:50]:
        row = dict(raw)
        if "matched_record_id" in row:
            row["id"] = row["matched_record_id"]
            row.update(row.get("matched_record_details") or {})
        rows.append(row)
    pagination = payload.get("pagination") or {}
    page = int(params.get("page", 1))
    has_more = len(data) > 50 or pagination.get("total_pages", page) > page
    return ResultSet(
        kind=kind,
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
            ["Ranked search results are bounded and are not exhaustive."]
            if operation.startswith("search_")
            else []
        ),
    )
