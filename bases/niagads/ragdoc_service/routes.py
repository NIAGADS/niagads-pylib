from fastapi import APIRouter, HTTPException, Query
from niagads.database.ragdoc.schema import (
    ChunkEmbedding,
    ChunkMetadata,
    Document,
    IngestionJob,
)
from niagads.ragdoc_service.dependencies import (
    AsyncSessionDependency,
    EmbeddingGeneratorDependency,
)
from niagads.ragdoc_service.models import (
    ChunkResponse,
    DocumentResponse,
    JobStatusResponse,
    RetrievalRequest,
    RetrievalResponse,
)
from sqlalchemy import Select, func, select


router = APIRouter()


@router.get("/status", summary="get-api-status")
async def status():
    """Return a simple health/status payload for the read API."""
    return {"message": "document knowledgebase read api is available"}


@router.get("/jobs", response_model=list[JobStatusResponse], summary="list-jobs")
async def list_jobs(session: AsyncSessionDependency):
    """List ingestion jobs ordered newest first."""
    statement: Select = select(IngestionJob).order_by(IngestionJob.creation_date.desc())
    result = await session.execute(statement)

    return [
        JobStatusResponse(
            job_id=job.ingestion_job_id,
            url=job.url,
            status=job.status,
            max_pages=job.max_pages,
            num_documents=job.num_documents,
            num_chunks=job.num_chunks,
            num_embeddings=job.num_embeddings,
            error=job.error_message,
            created=job.creation_date,
            started=job.start_date,
            ended=job.end_date,
        )
        for job in result.scalars().all()
    ]


@router.get(
    "/documents", response_model=list[DocumentResponse], summary="list-documents"
)
async def list_documents(
    session: AsyncSessionDependency,
    limit: int = Query(default=100, ge=1, le=1000),
):
    """List stored documents."""
    statement: Select = (
        select(Document)
        .order_by(Document.retrieval_ts.desc(), Document.document_id.desc())
        .limit(limit)
    )
    result = await session.execute(statement)

    return [
        DocumentResponse(
            document_id=document.document_id,
            url=document.url,
            document_type=document.document_type,
            retrieval_status=document.retrieval_status,
            retrieval_ts=document.retrieval_ts,
        )
        for document in result.scalars().all()
    ]


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="get-document",
)
async def get_document(document_id: int, session: AsyncSessionDependency):
    """Fetch a single stored document by primary key."""
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentResponse(
        document_id=document.document_id,
        url=document.url,
        document_type=document.document_type,
        retrieval_status=document.retrieval_status,
        retrieval_ts=document.retrieval_ts,
    )


@router.get(
    "/documents/{document_id}/chunks",
    response_model=list[ChunkResponse],
    summary="list-document-chunks",
)
async def list_document_chunks(
    document_id: int,
    session: AsyncSessionDependency,
    limit: int = Query(default=200, ge=1, le=2000),
):
    """List chunks for a single document."""
    statement: Select = (
        select(ChunkMetadata)
        .where(ChunkMetadata.document_id == document_id)
        .order_by(ChunkMetadata.chunk_index.asc())
        .limit(limit)
    )
    result = await session.execute(statement)

    return [
        ChunkResponse(
            chunk_metadata_id=chunk.chunk_metadata_id,
            document_id=chunk.document_id,
            document_section=chunk.document_section,
            chunk_index=chunk.chunk_index,
            chunk_text=chunk.chunk_text,
        )
        for chunk in result.scalars().all()
    ]


@router.post("/retrieve", response_model=RetrievalResponse, summary="retrieve-context")
async def retrieve_context(
    request: RetrievalRequest,
    session: AsyncSessionDependency,
    embedding_generator: EmbeddingGeneratorDependency,
):
    """
    Retrieve chunk context using semantic similarity with pgvector.

    Returns ranked knowledgebase chunks with citation-ready information:
    - Chunk text
    - Document URL
    - Section information
    - Cosine similarity score (0-1, where 1 is most similar)
    """
    query_embedding = embedding_generator.generate(
        request.query, normalize=True, as_list=True
    )

    # cosine_distance ranges from 0 (identical) to 2 (opposite)
    # Convert to a 0-1 similarity score for callers.
    statement: Select = (
        select(
            ChunkMetadata,
            Document,
            ChunkEmbedding,
            (1 - (ChunkEmbedding.embedding.cosine_distance(query_embedding) / 2)).label(
                "similarity_score"
            ),
        )
        .join(
            ChunkEmbedding,
            ChunkEmbedding.chunk_metadata_id == ChunkMetadata.chunk_metadata_id,
        )
        .join(Document, Document.document_id == ChunkMetadata.document_id)
        .where(ChunkEmbedding.embedding.isnot(None))
        .order_by(func.desc("similarity_score"))
        .limit(request.limit)
    )
    result = await session.execute(statement)

    results = []
    for chunk_metadata, document, chunk_embedding, similarity_score in result.all():
        results.append(
            ChunkResponse(
                chunk_metadata_id=chunk_metadata.chunk_metadata_id,
                document_id=chunk_metadata.document_id,
                document_section=chunk_metadata.document_section,
                chunk_index=chunk_metadata.chunk_index,
                chunk_text=chunk_metadata.chunk_text,
                url=document.url,
                score=float(similarity_score),
            )
        )

    return RetrievalResponse(query=request.query, results=results)
