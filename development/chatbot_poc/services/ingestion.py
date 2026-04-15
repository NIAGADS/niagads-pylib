# TODO:
# - decide re-ingestion behavior for existing documents and chunks
# - persist retrieval failures and status updates consistently per page
# - improve crawl hygiene: robots.txt, rate limiting, trap-link filtering,
#   and stronger URL/content deduplication
# - improve content extraction: page metadata, better boilerplate removal,
#   and site-specific block handling for docs/table-heavy pages
# - add tests for the end-to-end ingestion flow

from collections import deque
from datetime import datetime
from urllib.parse import urldefrag, urljoin, urlparse

from aiohttp import ClientSession
from lxml import html
from niagads.common.core import ComponentBaseMixin
from niagads.database.session import DatabaseSessionManager
from niagads.database.types import RAGDocType
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.nlp.helpers import chunk_text
from pydantic import BaseModel, Field
from sqlalchemy import select

from development.chatbot_poc.database.tables import (
    ChunkEmbedding,
    ChunkMetadata,
    Document,
)


class DocumentIngestionRequest(BaseModel):
    """Request to ingest a website starting from a root URL.

    Attributes:
        url: Root source location to fetch and crawl.
        document_type: Classification used to guide downstream handling.
        max_pages: Optional crawl limit for this request. If None, the crawler
            continues until the in-scope queue is exhausted or the default
            service safety cap is reached.
    """

    url: str
    document_type: RAGDocType = RAGDocType.DOCUMENT
    max_pages: int | None = Field(default=None, gt=0)


class RetrievedDocument(BaseModel):
    """Normalized document content returned by a retriever.

    Attributes:
        url: Canonical source URL.
        content: Combined extracted text content for document-level hashing.
        content_blocks: Structured content blocks extracted from the page.
        document_type: Classification propagated from the ingestion request.
    """

    url: str
    content: str
    content_blocks: list["ContentBlock"]
    document_type: RAGDocType


class ContentBlock(BaseModel):
    """Structured content block extracted from a scraped page.

    Attributes:
        text: Informative text extracted from a single content block.
        section: Nearest heading or logical section label for the block.
    """

    text: str
    section: str = "FULL"


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
    """Summary of a completed website ingestion run.

    Attributes:
        url: Root URL that was ingested.
        num_documents: Number of documents persisted for the website crawl.
        num_chunks: Number of chunks stored across scraped pages.
        num_embeddings: Number of embeddings persisted across scraped pages.
    """

    url: str
    num_documents: int
    num_chunks: int
    num_embeddings: int


class DocumentIngestionService(ComponentBaseMixin):
    """Coordinate retrieval, chunking, embedding, and persistence."""

    _DEFAULT_MAX_PAGES = 250
    _STRIP_TAGS = (
        "script",
        "style",
        "noscript",
        "header",
        "footer",
        "nav",
        "aside",
        "form",
        "svg",
        "canvas",
        "iframe",
    )
    _SKIP_EXTENSIONS = (
        ".css",
        ".js",
        ".json",
        ".xml",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".webp",
        ".ico",
        ".pdf",
        ".zip",
    )
    _BLOCK_TAGS = ("p", "li", "pre", "blockquote", "td", "th")
    _HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")
    _MAX_BLOCK_SIZE = 2000

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
        self._embedding_model = embedding_model

    async def ingest(
        self, request: DocumentIngestionRequest
    ) -> DocumentIngestionResult:
        """Ingest a document from retrieval through persistence.

        Args:
            request: Ingestion request describing the source URL and type.

        Returns:
            Summary of the persisted document, chunk, and embedding counts.

        Raises:
            ValueError: If the embedding provider returns a different number of
                vectors than the number of generated chunks.
        """

        documents = await self._retrieve_documents(request)
        num_documents = 0
        num_chunks = 0
        num_embeddings = 0

        async with self._database_session_manager.session_ctx() as session:
            for document in documents:
                document_id, should_index = await self._store_document(session, document)
                if not should_index:
                    continue

                num_documents += 1
                chunks = self._chunk_document(document)
                if not chunks:
                    continue

                vectors = self._embedding_generator.generate(
                    [chunk.text for chunk in chunks]
                )

                # Each chunk must have exactly one embedding so downstream
                # persistence can preserve chunk-to-vector correspondence.
                if len(vectors) != len(chunks):
                    raise ValueError(
                        "Embedding provider returned a mismatched number of vectors"
                    )

                chunk_ids = await self._store_chunks(session, document_id, chunks)
                num_chunks += len(chunks)
                num_embeddings += await self._store_embeddings(
                    session, chunk_ids, chunks, vectors
                )

            await session.commit()

        return DocumentIngestionResult(
            url=request.url,
            num_documents=num_documents,
            num_chunks=num_chunks,
            num_embeddings=num_embeddings,
        )

    async def _retrieve_documents(
        self, request: DocumentIngestionRequest
    ) -> list[RetrievedDocument]:
        """Fetch and normalize all in-scope documents for a website crawl."""
        root_url = self._normalize_url(request.url)
        root_netloc = urlparse(root_url).netloc
        max_pages = (
            self._DEFAULT_MAX_PAGES if request.max_pages is None else request.max_pages
        )
        queue = deque([root_url])
        visited = set()
        documents = []

        async with ClientSession() as session:
            while queue and len(visited) < max_pages:
                url = queue.popleft()
                if url in visited:
                    continue

                visited.add(url)

                try:
                    async with session.get(url) as response:
                        content_type = response.headers.get("Content-Type", "")
                        if "html" not in content_type.lower():
                            continue
                        source = await response.text()
                except Exception:
                    self.logger.exception(f"Failed to scrape {url}")
                    continue

                content_blocks, links = self._extract_page_content(url, source)
                if content_blocks:
                    documents.append(
                        RetrievedDocument(
                            url=url,
                            content=" ".join(block.text for block in content_blocks),
                            content_blocks=content_blocks,
                            document_type=request.document_type,
                        )
                    )

                for link in links:
                    normalized_link = self._normalize_url(urljoin(url, link))
                    if self._is_in_scope_link(normalized_link, root_netloc):
                        queue.append(normalized_link)

        return documents

    def _chunk_document(self, document: RetrievedDocument) -> list[TextChunk]:
        """Split structured content blocks into stored chunk units."""
        chunks = []
        chunk_index = 0

        for block in document.content_blocks:
            block_chunks = (
                [block.text]
                if len(block.text) <= self._MAX_BLOCK_SIZE
                else chunk_text(block.text, max_chunk_size=self._MAX_BLOCK_SIZE)
            )

            for chunk in block_chunks:
                chunks.append(
                    TextChunk(
                        text=chunk,
                        chunk_index=chunk_index,
                        document_section=block.section,
                    )
                )
                chunk_index += 1

        return chunks

    async def _store_document(self, session, document: RetrievedDocument) -> tuple[int, bool]:
        """Persist the document record and return its primary key and index flag."""
        content_hash = TextEmbeddingGenerator.hash_text(document.content)
        query = select(Document).where(
            Document.url == document.url, Document.content_hash == content_hash
        )
        existing = (await session.execute(query)).scalar_one_or_none()
        if existing is not None:
            existing.retrieval_ts = datetime.now()
            existing.retrieval_status = "SUCCESS"
            await session.flush()
            return existing.document_id, False

        record = Document(
            url=document.url,
            document_type=document.document_type,
            content_hash=content_hash,
            retrieval_ts=datetime.now(),
            retrieval_status="SUCCESS",
        )
        session.add(record)
        await session.flush()
        return record.document_id, True

    async def _store_chunks(
        self, session, document_id: int, chunks: list[TextChunk]
    ) -> list[int]:
        """Persist chunk records and return their primary keys."""
        document = await session.get(Document, document_id)
        records = [
            ChunkMetadata(
                document_id=document_id,
                document_type=document.document_type,
                document_hash=document.content_hash,
                chunk_hash=TextEmbeddingGenerator.hash_text(chunk.text),
                chunk_text=chunk.text,
                chunk_index=chunk.chunk_index,
                start_offset=chunk.start_offset,
                end_offset=chunk.end_offset,
                document_section=chunk.document_section,
                chunk_id=f"{document_id}_{chunk.chunk_index}",
            )
            for chunk in chunks
        ]
        session.add_all(records)
        await session.flush()
        return [record.chunk_metadata_id for record in records]

    async def _store_embeddings(
        self,
        session,
        chunk_ids: list[int],
        chunks: list[TextChunk],
        embeddings: list[list[float]],
    ) -> int:
        """Persist chunk embeddings and return the number stored."""
        records = [
            ChunkEmbedding(
                chunk_metadata_id=chunk_id,
                chunk_hash=TextEmbeddingGenerator.hash_text(chunk.text),
                embedding=embedding,
                embedding_model=(
                    None
                    if self._embedding_model is None
                    else str(self._embedding_model)
                ),
            )
            for chunk_id, chunk, embedding in zip(chunk_ids, chunks, embeddings)
        ]
        session.add_all(records)
        await session.flush()
        return len(records)

    def _extract_page_content(
        self, url: str, source: str
    ) -> tuple[list[ContentBlock], list[str]]:
        """Extract informative content blocks and crawl links from an HTML page."""
        root = html.fromstring(source)
        root.make_links_absolute(url)

        for tag in self._STRIP_TAGS:
            for element in root.xpath(f"//{tag}"):
                element.drop_tree()

        links = [link for _, _, link, _ in root.iterlinks() if link]
        content_blocks = self._extract_content_blocks(root)
        return content_blocks, links

    def _extract_content_blocks(self, root) -> list[ContentBlock]:
        """Extract structured informative blocks from a cleaned DOM tree."""
        containers = root.xpath("//main | //article")
        scope = containers[0] if containers else root.find("body") or root
        current_section = "FULL"
        content_blocks = []

        for element in scope.iter():
            tag = getattr(element, "tag", None)
            if tag not in self._HEADING_TAGS and tag not in self._BLOCK_TAGS:
                continue

            text = " ".join(element.text_content().split())
            if not text:
                continue

            if tag in self._HEADING_TAGS:
                current_section = text
                continue

            if content_blocks and content_blocks[-1].text == text:
                continue

            content_blocks.append(ContentBlock(text=text, section=current_section))

        return content_blocks

    def _normalize_url(self, url: str) -> str:
        """Normalize crawled URLs so duplicate pages collapse to one target."""
        normalized, _ = urldefrag(url.strip())
        return normalized.rstrip("/")

    def _is_in_scope_link(self, url: str, root_netloc: str) -> bool:
        """Return whether a discovered URL should be crawled."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.netloc != root_netloc:
            return False
        if any(parsed.path.lower().endswith(ext) for ext in self._SKIP_EXTENSIONS):
            return False
        return True

    async def close(self):
        """Close pooled database connections owned by the service."""
        await self._database_session_manager.close()
