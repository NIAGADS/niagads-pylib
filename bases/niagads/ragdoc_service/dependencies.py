from typing import Annotated

from fastapi import Depends
from niagads.ragdoc_service.config import Settings
from sqlalchemy.ext.asyncio import AsyncSession

from niagads.database.session import DatabaseSessionManager
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.nlp.llm_types import LLM


ROUTE_SESSION_MANAGER = DatabaseSessionManager(
    connection_string=Settings.from_env().DATABASE_URI,
)

AsyncSessionDependency = Annotated[AsyncSession, Depends(ROUTE_SESSION_MANAGER)]


# Instantiate the embedding generator once at module load time
EMBEDDING_GENERATOR = TextEmbeddingGenerator(model=LLM.ALL_MINILM_L6_V2)


def get_embedding_generator() -> TextEmbeddingGenerator:
    """Dependency to provide the shared TextEmbeddingGenerator instance."""
    return EMBEDDING_GENERATOR


EmbeddingGeneratorDependency = Annotated[
    TextEmbeddingGenerator, Depends(get_embedding_generator)
]
