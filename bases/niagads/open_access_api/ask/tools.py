"""Typed tool definitions adapting existing API operations, never database access."""

from typing import Annotated, Literal

import httpx
from niagads.api.common.constants import MAX_NUM_PAGES
from niagads.api.common.types import ResponseContent
from niagads.common.types import Entity
from niagads.open_access_api.ask.api_client import retrieve
from niagads.open_access_api.ask.contracts import Presentation
from niagads.open_access_api.ask.operations import SEARCH_OPERATIONS
from pydantic import Field
from pydantic_ai import ModelRetry, RunContext


async def _execute(ctx: RunContext[dict], operation: str, parameters: dict) -> dict:
    """Retrieve through the existing API and expose a compact evidence summary."""
    try:
        result = await retrieve(ctx.deps["client"], operation, parameters)
        ctx.deps["store"].add(result)
        return ctx.deps["store"].summary(result.id)
    except NotImplementedError:
        status = "unsupported"
        detail = "This API operation or its required embedding model is unavailable."
    except (httpx.HTTPError, ValueError):
        status = "retrieval_error"
        detail = "API retrieval failed or exceeded prototype limits; narrow the query or retry."
    ctx.deps.setdefault("warnings", []).append(detail)
    ctx.deps.setdefault("failures", []).append(status)
    return {"status": status, "detail": detail}


async def search_resources(
    ctx: RunContext[dict],
    query: str,
    entity: Entity,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> dict:
    """Search gene/track candidates; semantic similarity is not association evidence."""
    operation = SEARCH_OPERATIONS.get(entity)
    if operation is None:
        detail = (
            "Variant semantic search remains planned; use a variant identifier."
            if entity == Entity.VARIANT
            else f"Semantic search for {entity.value} is not supported."
        )
        ctx.deps.setdefault("warnings", []).append(detail)
        ctx.deps.setdefault("failures", []).append("unsupported")
        return {"status": "unsupported", "detail": detail}
    return await _execute(ctx, operation, {"query": query, "limit": limit})


async def get_gene(ctx: RunContext[dict], gene: str) -> dict:
    """Retrieve an existing gene record by identifier or symbol."""
    return await _execute(ctx, "gene", {"gene": gene})


async def get_variant(ctx: RunContext[dict], variant: str) -> dict:
    """Retrieve variant records by refSNP, structural, or positional allelic ID."""
    return await _execute(ctx, "variant", {"variant": variant})


async def get_track(ctx: RunContext[dict], track: str) -> dict:
    """Retrieve track metadata by its stable track identifier."""
    return await _execute(ctx, "track", {"track": track})


async def get_gene_structure(ctx: RunContext[dict], gene: str) -> dict:
    """Discover transcript IDs/locations before selecting a transcript for associations."""
    summary = await _execute(ctx, "gene_structure", {"gene": gene})
    if "result_id" in summary:
        result = ctx.deps["store"].get(summary["result_id"])
        transcripts = [t for row in result.rows for t in row.get("transcripts", [])]
        summary["transcripts"] = [
            {k: t[k] for k in ("id", "name", "location") if k in t}
            for t in transcripts[:20]
        ]
        summary["transcripts_truncated"] = len(transcripts) > 20
    return summary


async def get_gene_associations(
    ctx: RunContext[dict],
    gene: str,
    page: Annotated[int, Field(ge=1, le=MAX_NUM_PAGES)] = 1,
    flank: Annotated[int, Field(ge=0, le=1000000)] = 0,
    content: Literal[
        ResponseContent.FULL, ResponseContent.SUMMARY
    ] = ResponseContent.FULL,
) -> dict:
    """Retrieve gene associations; use summary content for counts by track."""
    operation = (
        "gene_associations_summary"
        if content == ResponseContent.SUMMARY
        else "gene_associations"
    )
    return await _execute(ctx, operation, {"gene": gene, "page": page, "flank": flank})


async def get_variant_associations(
    ctx: RunContext[dict],
    variant: str,
    page: Annotated[int, Field(ge=1, le=MAX_NUM_PAGES)] = 1,
    flank: Annotated[int, Field(ge=0, le=1000000)] = 0,
    content: Literal[
        ResponseContent.FULL, ResponseContent.SUMMARY
    ] = ResponseContent.FULL,
) -> dict:
    """Retrieve variant associations; use summary content for counts by track."""
    operation = (
        "variant_associations_summary"
        if content == ResponseContent.SUMMARY
        else "variant_associations"
    )
    return await _execute(
        ctx,
        operation,
        {"variant": variant, "page": page, "flank": flank},
    )


async def get_transcript_associations(
    ctx: RunContext[dict],
    gene: str,
    transcript: str,
    content: Literal[
        ResponseContent.FULL, ResponseContent.SUMMARY
    ] = ResponseContent.FULL,
) -> dict:
    """Resolve the exact transcript span through gene structure, then query its region."""
    summary = await _execute(ctx, "gene_structure", {"gene": gene})
    if "result_id" not in summary:
        return summary
    result = ctx.deps["store"].get(summary["result_id"])
    transcripts = [t for row in result.rows for t in row.get("transcripts", [])]
    selected = [t for t in transcripts if t.get("id") == transcript]
    if len(selected) != 1 or not selected[0].get("location"):
        ctx.deps.setdefault("failures", []).append("clarification")
        return {
            "status": "clarification",
            "detail": "Select a transcript ID with a location from the gene structure.",
        }
    return await _execute(
        ctx,
        (
            "region_associations_summary"
            if content == ResponseContent.SUMMARY
            else "region_associations"
        ),
        {"region": selected[0]["location"]},
    )


async def get_region_associations(
    ctx: RunContext[dict],
    region: str,
    content: Literal[
        ResponseContent.FULL, ResponseContent.SUMMARY
    ] = ResponseContent.FULL,
) -> dict:
    """Request regional associations or per-track counts; may return 501."""
    operation = (
        "region_associations_summary"
        if content == ResponseContent.SUMMARY
        else "region_associations"
    )
    return await _execute(ctx, operation, {"region": region})


async def find_phenotype_genes(ctx: RunContext[dict], phenotype: str) -> dict:
    """Report phenotype-to-gene retrieval readiness; never substitute semantic hits."""
    detail = (
        "Phenotype-associated gene retrieval is pending local ORM/API integration. "
        "The intended response combines curated-list and +/-10 kb proximity "
        "evidence with data_source provenance; semantic search is not equivalent."
    )
    ctx.deps.setdefault("warnings", []).append(detail)
    ctx.deps.setdefault("failures", []).append("unsupported")
    return {"status": "unsupported", "phenotype": phenotype, "detail": detail}


async def find_api_operations(ctx: RunContext[dict], query: str) -> dict:
    """Search the application's own OpenAPI operation descriptions and parameters."""
    words = query.casefold().split()
    matches = []
    for path, methods in ctx.deps["spec"].get("paths", {}).items():
        for method, operation in methods.items():
            if method != "get":
                continue
            text = f"{path} {operation.get('summary', '')}".casefold()
            if not any(word in text for word in words):
                continue
            matches.append(
                {
                    "method": "GET",
                    "path": path,
                    "operation_id": operation.get("operationId"),
                    "summary": operation.get("summary", "")[:300],
                    "x-status": operation.get("x-status"),
                    "parameters": [
                        {
                            k: p[k]
                            for k in (
                                "name",
                                "in",
                                "required",
                                "schema",
                                "examples",
                            )
                            if k in p
                        }
                        for p in operation.get("parameters", [])[:12]
                    ],
                }
            )
            if len(matches) == 10:
                return {"operations": matches, "truncated": True}
    return {"operations": matches, "truncated": False}


async def present_results(
    ctx: RunContext[dict],
    result_id: str,
    component: Literal["table", "association_source_bar"] = "table",
    title: str = "Retrieved evidence",
) -> dict:
    """Select a registered component for data retrieved during this run only."""
    try:
        presentation = Presentation(
            component=component, result_id=result_id, title=title
        )
        ctx.deps["store"].validate_presentation(presentation)
        if len(ctx.deps["store"].presentations) >= 6:
            raise ValueError("Presentation limit reached")
        ctx.deps["store"].presentations.append(presentation)
    except ValueError as exc:
        raise ModelRetry(str(exc)) from exc
    return {
        "status": "validated",
        "result_id": result_id,
        "component": component,
    }
