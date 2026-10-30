"""Typed tool definitions adapting existing API operations, never database access."""

import logging
from typing import Annotated, Literal

from niagads.api.common.constants import MAX_NUM_PAGES
from niagads.api.common.types import ResponseContent
from niagads.common.types import Entity
from niagads.open_access_api.ask.api_client import resolve_feature_location, retrieve
from niagads.open_access_api.ask.contracts import (
    AskIssue,
    PresentationIntent,
    ResultFilter,
)
from niagads.open_access_api.ask.operations import SEARCH_OPERATIONS
from niagads.open_access_api.ask.planning import GeneEvidence, QueryClarification
from pydantic import Field
from pydantic_ai import ModelRetry, RunContext


async def _execute(
    ctx: RunContext[dict],
    operation: str,
    parameters: dict,
    *,
    transcript: str | None = None,
    evidence_fields: list[GeneEvidence] | None = None,
) -> dict:
    """Retrieve through the existing API and expose a compact evidence summary."""
    if evidence_fields is None:
        plan = ctx.deps.get("query_plan")
        evidence_fields = plan.gene_evidence if plan else []
    result = await retrieve(ctx.deps["client"], operation, parameters)
    ctx.deps["store"].add(result)
    return ctx.deps["store"].summary(
        result.id,
        gene_evidence=evidence_fields,
        transcript=transcript,
    )


async def search_resources(
    ctx: RunContext[dict],
    text: str,
    entity: Entity,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
) -> dict:
    """Search datasets (entity=track) or genes; similarity is not association evidence."""
    operation = SEARCH_OPERATIONS.get(entity)
    if operation is None:
        logging.getLogger("uvicorn.error.niagads.ask").info(
            "No search operation registered for entity=%s", entity.value
        )
        return {"status": "unsupported", "entity": entity.value}
    return await _execute(ctx, operation, {"text": text, "limit": limit})


async def get_gene(
    ctx: RunContext[dict],
    gene: str,
    content: Literal[
        ResponseContent.FULL, ResponseContent.SUMMARY
    ] = ResponseContent.SUMMARY,
    evidence_fields: Annotated[list[GeneEvidence] | None, Field(max_length=6)] = None,
) -> dict:
    """Look up a gene; request full content for needed annotations or curated lists.

    Args:
        ctx (RunContext[dict]): Agent context with the API client and result store.
        gene (str): Gene identifier or symbol.
        content (ResponseContent): Summary or full gene record content.
        evidence_fields (list[GeneEvidence] | None): Needed annotations, selectable
            as evidence emerges; omitted uses the initial interpretation.

    Returns:
        dict: Compact record evidence, or semantic candidates if no record matches.
    """
    operation = "gene_full" if content == ResponseContent.FULL else "gene"
    summary = await _execute(
        ctx, operation, {"gene": gene}, evidence_fields=evidence_fields
    )
    if summary["count"] == 0:
        return await search_resources(ctx, gene, Entity.GENE)
    return summary


async def get_variant(ctx: RunContext[dict], variant: str) -> dict:
    """Retrieve variant records by refSNP, structural, or positional allelic ID."""
    return await _execute(ctx, "variant", {"variant": variant})


async def get_feature_location(
    ctx: RunContext[dict],
    identifier: str,
    flank: Annotated[int, Field(ge=0, le=1000000)] = 0,
) -> dict:
    """Resolve a gene/variant span; use flank=10000 for unspecified 'near' scope.

    Args:
        ctx (RunContext[dict]): Agent context containing the API client.
        identifier (str): Gene symbol, gene ID, or variant ID.
        flank (int): Bases to extend on both sides; zero for the exact footprint.

    Returns:
        dict: Resolved region, coordinates, and the requested flanking distance.
    """
    region = await resolve_feature_location(ctx.deps["client"], identifier, flank)
    return {
        "region": f"{region.chromosome}:{region.start}-{region.end}",
        "chr": str(region.chromosome),
        "start": region.start,
        "end": region.end,
        "flank": flank,
    }


async def get_region_variants(ctx: RunContext[dict], region: str) -> dict:
    """Retrieve variant records in a resolved span, including ADSP flags.

    Use for variant inventories, not association annotations or association plots.
    Retrieve association evidence with the association tools instead.
    Each region must span fewer than 100,000 bp. At most the first 5,000 variants
    ordered by position are retrieved. Preserve truncation warnings; filtering
    these records does not search the omitted variants.

    Args:
        ctx (RunContext[dict]): Agent context with the API client and result store.
        region (str): Region in chrN:start-end or N:start-end format.

    Returns:
        dict: Evidence summary referencing the retrieved records.
    """
    return await _execute(ctx, "region_variants", {"region": region})


async def get_track(ctx: RunContext[dict], track: str) -> dict:
    """Retrieve track metadata by its stable track identifier."""
    return await _execute(ctx, "track", {"track": track})


async def get_track_data(
    ctx: RunContext[dict],
    track_ids: list[str],
    loc: str,
    flank: Annotated[int | None, Field(ge=0)] = None,
) -> dict:
    """Declare future gene/span/variant track-data retrieval without an HTTP call."""
    detail = "Genomic data retrieval for selected tracks is not implemented; track metadata is not genomic feature data."
    ctx.deps["issues"].append(
        AskIssue(code="unsupported", operation="get_track_data", message=detail)
    )
    ctx.deps["failures"].append("unsupported")
    return {
        "status": "unsupported",
        "detail": detail,
        "requested": {"track_ids": track_ids, "loc": loc, "flank": flank},
    }


async def get_gene_structure(
    ctx: RunContext[dict],
    gene: str,
    transcript: str | None = None,
    evidence_fields: Annotated[list[GeneEvidence] | None, Field(max_length=6)] = None,
) -> dict:
    """Return transcript identities/spans; request exons only when needed.

    Per-call evidence overrides the preliminary interpretation. Stored records
    stay intact, including transcripts beyond the compact model preview.
    """
    if evidence_fields is None:
        plan = ctx.deps.get("query_plan")
        evidence_fields = list(plan.gene_evidence) if plan else []
        if GeneEvidence.TRANSCRIPTS not in evidence_fields:
            evidence_fields.append(GeneEvidence.TRANSCRIPTS)
    return await _execute(
        ctx,
        "gene_structure",
        {"gene": gene},
        transcript=transcript,
        evidence_fields=evidence_fields,
    )


async def clarify_request(
    ctx: RunContext[dict], clarification: QueryClarification
) -> dict:
    """Record a material question that returned evidence cannot resolve.

    Keep retrieved results for display while pausing only the dependent path.
    """
    ctx.deps["failures"].append("clarification")
    return {"status": "clarification", **clarification.model_dump(mode="json")}


async def get_gene_associations(
    ctx: RunContext[dict],
    gene: str,
    page: Annotated[int, Field(ge=1, le=MAX_NUM_PAGES)] = 1,
    flank: Annotated[int, Field(ge=0, le=1000000)] = 0,
    content: Literal[
        ResponseContent.FULL, ResponseContent.SUMMARY
    ] = ResponseContent.FULL,
) -> dict:
    """Retrieve gene association evidence, including reported phenotype/trait annotations.

    Use for variant associations at a named gene or locus, including locus plots.
    Associations are annotations, distinct from an inventory of nearby variants.
    Both full and summary content expose trait terms and source tracks to the agent.
    Summary content retains the API's association counts per track. Use returned
    track IDs with get_track for associated dataset metadata.
    """
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
        ctx.deps.setdefault("warnings", []).append(
            "Select a transcript ID with a location from the gene structure."
        )
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
    """Retrieve association annotations in a region, not a variant inventory.

    Use full content for association plots; summary returns per-track counts.
    The region must span fewer than 100,000 bp, including both endpoints.
    """
    operation = (
        "region_associations_summary"
        if content == ResponseContent.SUMMARY
        else "region_associations"
    )
    return await _execute(ctx, operation, {"region": region})


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
    ctx: RunContext[dict], presentation: PresentationIntent
) -> dict:
    """Record view/plot preferences for retrieved data; the UI selects its adapters."""
    try:
        ctx.deps["store"].validate_presentation(presentation)
        if len(ctx.deps["store"].presentations) >= 6:
            raise ValueError("Presentation limit reached")
        ctx.deps["store"].presentations.append(presentation)
    except (ValueError, RuntimeError) as exc:
        raise ModelRetry(str(exc)) from exc
    return {"status": "recorded", **presentation.model_dump(mode="json")}


async def filter_results(
    ctx: RunContext[dict],
    result_id: str,
    filters: Annotated[list[ResultFilter], Field(min_length=1, max_length=10)],
    title: str = "Filtered records",
) -> dict:
    """Request frontend equality filters on retrieved rows without another query.

    Args:
        ctx (RunContext[dict]): Agent context containing this run's results.
        result_id (str): Reference to an already retrieved result.
        filters (list[ResultFilter]): Exact scalar field matches, combined by AND.
        title (str): Title of the filtered table.

    Returns:
        dict: Recorded presentation intent and matching count for loaded rows.
    """
    try:
        result = ctx.deps["store"].get(result_id)
        fields = set()
        matching_count = 0
        for row in result.rows:
            fields.update(row)
            matching_count += all(
                isinstance(row.get(item.field), bool) == isinstance(item.value, bool)
                and row.get(item.field) == item.value
                for item in filters
            )
        for requested in filters:
            if result.rows and requested.field not in fields:
                raise ValueError(f"Unknown filter field: {requested.field}")
        intent = PresentationIntent(
            result_id=result_id, view="table", title=title, filters=filters
        )
    except (ValueError, RuntimeError) as exc:
        raise ModelRetry(str(exc)) from exc
    recorded = await present_results(ctx, intent)
    recorded["matching_count"] = matching_count
    recorded["loaded_count"] = len(result.rows)
    return recorded
