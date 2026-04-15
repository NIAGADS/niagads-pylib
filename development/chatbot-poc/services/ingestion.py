from niagads.common.core import ComponentBaseMixin
from niagads.database.session import DatabaseSessionManager
from niagads.database.types import RAGDocType
from niagads.nlp.embeddings import TextEmbeddingGenerator
from pydantic import BaseModel


class DocumentIngestionRequest(BaseModel):
    """Request to ingest a single source document by URL.

    Attributes:
        url: Source location to fetch and process.
        document_type: Classification used to guide downstream handling.
    """

    url: str
    document_type: RAGDocType = RAGDocType.DOCUMENT


class RetrievedDocument(BaseModel):
    """Normalized document content returned by a retriever.

    Attributes:
        url: Canonical source URL.
        content: Extracted text content to chunk and embed.
        document_type: Classification propagated from the ingestion request.
    """

    url: str
    content: str
    document_type: RAGDocType


class TextChunk(BaseModel):
    """Chunked text unit derived from a retrieved document.

    Attributes:
        text: Chunk content to embed and retrieve later.
        chunk_index: Zero-based position of the chunk in the source document.
        start_offset: Optional starting character offset in the source text.
        end_offset: Optional ending character offset in the source text.
        document_section: Logical section label for citation and grouping.
    """

    text: str
    chunk_index: int
    start_offset: int | None = None
    end_offset: int | None = None
    document_section: str = "FULL"


class DocumentIngestionResult(BaseModel):
    """Summary of a completed ingestion run.

    Attributes:
        url: Source URL that was ingested.
        document_id: Primary key of the persisted document record.
        num_chunks: Number of chunks stored for the document.
        num_embeddings: Number of embeddings persisted for those chunks.
    """

    url: str
    document_id: int
    num_chunks: int
    num_embeddings: int


class DocumentIngestionService(ComponentBaseMixin):
    """Coordinate retrieval, chunking, embedding, and persistence."""

    def __init__(
        self,
        database_uri: str,
        embedding_model=None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(debug=debug, verbose=verbose)
        self._database_session_manager = DatabaseSessionManager(database_uri)
        self._embedding_generator = (
            TextEmbeddingGenerator()
            if embedding_model is None
            else TextEmbeddingGenerator(embedding_model)
        )

    async def ingest(self, request: DocumentIngestionRequest) -> DocumentIngestionResult:
        """Ingest a document from retrieval through persistence.

        Args:
            request: Ingestion request describing the source URL and type.

        Returns:
            Summary of the persisted document, chunk, and embedding counts.

        Raises:
            ValueError: If the embedding provider returns a different number of
                vectors than the number of generated chunks.
        """

        document = await self._retrieve_document(request)
        chunks = self._chunk_document(document)
        vectors = self._embedding_generator.generate([chunk.text for chunk in chunks])

        # Each chunk must have exactly one embedding so downstream persistence
        # can preserve chunk-to-vector correspondence.
        if len(vectors) != len(chunks):
            raise ValueError("Embedding provider returned a mismatched number of vectors")

        async with self._database_session_manager.session_ctx() as session:
            document_id = await self._store_document(session, document)
            chunk_ids = await self._store_chunks(session, document_id, chunks)
            num_embeddings = await self._store_embeddings(
                session, chunk_ids, chunks, vectors
            )
            await session.commit()

        return DocumentIngestionResult(
            url=document.url,
            document_id=document_id,
            num_chunks=len(chunks),
            num_embeddings=num_embeddings,
        )

    async def _retrieve_document(
        self, request: DocumentIngestionRequest
    ) -> RetrievedDocument:
        """Fetch and normalize the source document content."""
        raise NotImplementedError()

    def _chunk_document(self, document: RetrievedDocument) -> list[TextChunk]:
        """Split normalized document content into stored chunk units."""
        raise NotImplementedError()

    async def _store_document(
        self, session, document: RetrievedDocument
    ) -> int:
        """Persist the document record and return its primary key."""
        raise NotImplementedError()

    async def _store_chunks(
        self, session, document_id: int, chunks: list[TextChunk]
    ) -> list[int]:
        """Persist chunk records and return their primary keys."""
        raise NotImplementedError()

    async def _store_embeddings(
        self,
        session,
        chunk_ids: list[int],
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> int:
        """Persist chunk embeddings and return the number stored."""
        raise NotImplementedError()
