from datetime import datetime
from typing import Optional
from pydantic import Field
from niagads.common.models.base import CustomBaseModel


class JobStatusResponse(CustomBaseModel):
    job_id: int = Field(..., description="Unique job identifier")
    url: str = Field(..., description="Job resource URL")
    status: str = Field(..., description="Current job status")
    max_pages: Optional[int] = Field(None, description="Maximum number of pages")
    num_documents: Optional[int] = Field(
        None, description="Number of documents processed"
    )
    num_chunks: Optional[int] = Field(None, description="Number of chunks processed")
    num_embeddings: Optional[int] = Field(
        None, description="Number of embeddings generated"
    )
    error: Optional[str] = Field(None, description="Error message if job failed")
    created: Optional[datetime] = Field(None, description="Job creation timestamp")
    started: Optional[datetime] = Field(None, description="Job start timestamp")
    ended: Optional[datetime] = Field(None, description="Job end timestamp")


class DocumentResponse(CustomBaseModel):
    document_id: int = Field(..., description="Unique document identifier")
    url: str = Field(..., description="Document resource URL")
    document_type: str = Field(..., description="Type of the document")
    retrieval_status: str = Field(..., description="Status of document retrieval")
    retrieval_ts: Optional[datetime] = Field(None, description="Timestamp of retrieval")


class ChunkResponse(CustomBaseModel):
    chunk_metadata_id: int = Field(..., description="Unique chunk metadata identifier")
    document_id: int = Field(..., description="Associated document identifier")
    document_section: str = Field(..., description="Section of the document")
    chunk_index: int = Field(..., description="Index of the chunk in the document")
    chunk_text: Optional[str] = Field(None, description="Text content of the chunk")
    url: Optional[str] = Field(None, description="Chunk resource URL")
    score: Optional[float] = Field(None, description="Score or relevance of the chunk")


class RetrievalRequest(CustomBaseModel):
    query: str = Field(..., min_length=1, description="Retrieval query string")
    limit: int = Field(25, ge=1, le=200, description="Maximum chunks to return")


class RetrievalResponse(CustomBaseModel):
    query: str = Field(..., description="Retrieval query string")
    results: list[ChunkResponse] = Field(
        ..., description="Ranked context chunks for downstream RAG use"
    )
