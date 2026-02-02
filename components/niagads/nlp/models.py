"""Pydantic models for NLP operations."""

from typing import Optional
from pydantic import BaseModel, Field


class EmbeddingMatch(BaseModel):
    """
    Represents a match result from cosine similarity search against embeddings.

    Stores the matched text and its confidence score derived from cosine similarity.
    """

    query_text: str = Field(..., description="The searched text string")
    matched_text: str = Field(..., description="The matched text string")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "Confidence score from normalized similarity"
            "(0.0 to 1.0, where 1.0 is perfect match)"
        ),
    )
    embedding: Optional[list[float]] = Field(
        None, description="The embedding vector for the matched text."
    )
