"""Natural-language query endpoints for Open Access resources."""

from fastapi import APIRouter, Depends, Query
from niagads.api.common.models.context.request import Parameters
from niagads.api.common.models.context.response import ResponseConfiguration
from niagads.api.common.models.responses.records import RecordResponse
from niagads.api.common.parameters.response.pagination import page_param
from niagads.api.common.services.query import QueryEndpointService
from niagads.common.search.models.record import SearchMatch
from niagads.common.types import Entity
from niagads.open_access_api.dependencies import OpenAccessEndpointContext

router = APIRouter(prefix="/query", tags=["Query"])


async def query_service(
    query: str = Query(description="Natural-language query to search for."),
    limit: int = Query(
        default=10,
        gt=0,
        description="Maximum number of semantic matches per entity type.",
    ),
    page: int = Depends(page_param),
    context: OpenAccessEndpointContext = Depends(),
) -> QueryEndpointService:
    """Configure the query service with request parameters and response models.

    Args:
        query (str): Natural-language search text.
        limit (int): Maximum matches per entity type.
        page (int): One-based response page.
        context (OpenAccessEndpointContext): Request-scoped dependencies.

    Returns:
        QueryEndpointService: Configured semantic query service.
    """
    return QueryEndpointService(
        context=context,
        parameters=Parameters(query=query, limit=limit, page=page),
        response_config=ResponseConfiguration(
            response_model=RecordResponse,
            record_model=SearchMatch,
        ),
    )


@router.get(
    "",
    summary="Query tracks and genes",
    operation_id="queryResources",
    response_model=RecordResponse[SearchMatch],
)
async def query_resources(
    service: QueryEndpointService = Depends(query_service),
) -> RecordResponse[SearchMatch]:
    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.fetch_matches()
        from_cache = False
    return await service.generate_response(result, from_cache=from_cache)


@router.get(
    "/tracks",
    summary="Query track metadata",
    operation_id="queryTracks",
    response_model=RecordResponse[SearchMatch],
)
async def query_tracks(
    service: QueryEndpointService = Depends(query_service),
) -> RecordResponse[SearchMatch]:
    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.fetch_matches(Entity.TRACK)
        from_cache = False
    return await service.generate_response(result, from_cache=from_cache)


@router.get(
    "/genes",
    summary="Query genes",
    operation_id="queryGenes",
    response_model=RecordResponse[SearchMatch],
)
async def query_genes(
    service: QueryEndpointService = Depends(query_service),
) -> RecordResponse[SearchMatch]:
    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.fetch_matches(Entity.GENE)
        from_cache = False
    return await service.generate_response(result, from_cache=from_cache)


@router.get(
    "/variants",
    summary="Query variants (not yet implemented)",
    operation_id="queryVariants",
    response_model=RecordResponse[SearchMatch],
)
async def query_variants(
    service: QueryEndpointService = Depends(query_service),
) -> RecordResponse[SearchMatch]:
    result = await service.get_cached_response()
    from_cache = True
    if not result:
        result = await service.fetch_matches(Entity.VARIANT)
        from_cache = False
    return await service.generate_response(result, from_cache=from_cache)
