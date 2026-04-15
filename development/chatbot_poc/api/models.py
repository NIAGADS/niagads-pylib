from datetime import datetime

from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    job_id: int
    url: str
    status: str
    max_pages: int | None = None
    num_documents: int | None = None
    num_chunks: int | None = None
    num_embeddings: int | None = None
    error: str | None = None
    created: datetime | None = None
    started: datetime | None = None
    ended: datetime | None = None


class DocumentResponse(BaseModel):
    document_id: int
    url: str
    document_type: str
    retrieval_status: str
    retrieval_ts: datetime | None = None


class ChunkResponse(BaseModel):
    chunk_metadata_id: int
    document_id: int
    document_section: str
    chunk_index: int
    chunk_text: str | None = None
    url: str | None = None
    score: float | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[ChunkResponse]
