"""Semantic query services for Open Access resources."""

from niagads.api.common.services.base import BaseEndpointService
from niagads.api.common.services.embeddings import OpenRouterQueryEmbedding
from niagads.common.search.models.record import SearchMatch
from niagads.common.types import Entity
from niagads.database.genomicsdb.schema.dataset.track import Track
from niagads.database.genomicsdb.schema.gene.documents import Gene


class QueryEndpointService(BaseEndpointService):
    """Search track and gene documents using a query embedding."""

    async def semantic_search(self, entity: Entity | None = None) -> list[SearchMatch]:
        """Retrieve semantic matches for one entity or combine all supported entities.

        Args:
            entity (Entity | None): Entity to query, or None for tracks and genes.

        Returns:
            list[SearchMatch]: Semantic matches from the requested entities.
        """
        if entity == Entity.VARIANT:
            raise NotImplementedError("Variant semantic search is not yet implemented.")

        # TODO: Revise this hard-coded mapping and update it when OntologyTerm,
        # Variant, and other searchable entities are added.
        orm_models = {Entity.TRACK: Track, Entity.GENE: Gene}
        models = orm_models.values() if entity is None else (orm_models[entity],)
        embedding = await OpenRouterQueryEmbedding().generate(self._parameters.query)
        matches = []
        for orm_model in models:
            matches.extend(
                await orm_model.semantic_search_by_embedding(
                    self._context.database_session,
                    self._parameters.query,
                    embedding,
                    limit=self._parameters.limit,
                )
            )
        return matches
