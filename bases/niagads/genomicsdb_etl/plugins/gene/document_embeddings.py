"""Generate and load semantic chunk embeddings for gene documents."""

import json
from datetime import datetime
from typing import Optional

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.documents import Gene
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)
from niagads.database.genomicsdb.schema.ragdoc.types import (
    GeneDocumentSection,
    RAGDocType,
)
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.mixins import DocumentChunk, EmbeddingGeneratorContextMixin
from niagads.etl.plugins.parameters import BasePluginParams, EmbeddingParameterMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.utils.list import chunker
from pydantic import ValidationInfo, field_validator
from sqlalchemy import select

SECTIONS = {
    GeneDocumentSection.IDENTITY: [
        "source_id",
        "gene_type",
        "nomenclature",
        "chromosome",
        "associated_with_known_ad_locus",
    ],
    GeneDocumentSection.STRUCTURE: ["gene_structure"],
    GeneDocumentSection.ANNOTATION: ["functional_annotation", "memberships"],
    GeneDocumentSection.REFERENCES: ["xrefs", "publications"],
}


class EmbeddedGeneDocument(DocumentChunk):
    gene_id: int
    document_section: str
    document_hash: bytes
    chunk_hash: bytes
    embedding: Optional[list] = None  # so it can be set in batch

    @field_validator("chunk_hash", mode="before")
    @classmethod
    def generate_chunk_hash(cls, value: bytes, info: ValidationInfo) -> bytes:
        """Generate the chunk hash from its text."""

        return TextEmbeddingGenerator.hash_text(info.data["chunk_text"])


class GeneDocumentEmbeddingParams(BasePluginParams, EmbeddingParameterMixin):
    """Parameters for loading embeddings from the gene document view."""

    ...


@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=(
            "Load gene document embeddings grouped by identity, structure, "
            "annotation, and references. "
        ),
        affected_tables=[ChunkEmbedding, ChunkMetadata],
        parameter_model=GeneDocumentEmbeddingParams,
        load_strategy=ETLLoadStrategy.CHUNKED,
        operation=ETLOperation.INSERT,
        is_large_dataset=False,
        can_resume=True,
    )
)
class GeneDocumentEmbeddingLoader(AbstractBasePlugin, EmbeddingGeneratorContextMixin):
    """Read gene documents in keyset pages and persist their chunk embeddings."""

    _params: GeneDocumentEmbeddingParams

    def __init__(self, params, name=None, log_path=None, debug=False, verbose=False):
        super().__init__(params, name, log_path, debug, verbose)
        self._gene_records: list[Gene] = None
        self._embedded_doc_count = 0

    async def on_run_start(self, session) -> None:
        await EmbeddingGeneratorContextMixin.on_run_start(self, session)
        if self.is_etl_run:
            await self.set_table_ref(session, Gene)

            stmt = select(Gene)
            self._gene_records = (await session.execute(stmt)).scalars().all()
            self.logger.info(f"Retrieved {len(self._gene_records)} gene documents.")

    def extract(self):
        for record in self._gene_records:
            yield record

    def _generate_chunk_text(self, obj):
        chunk_text = json.dumps(obj)

    def _build_section_document(
        self, record: Gene, section: GeneDocumentSection
    ) -> tuple[bytes, dict]:
        """Build the complete JSON text for a gene document section."""
        documents = {
            field: value
            for field in SECTIONS[section]
            if (value := getattr(record, field)) is not None
        }

        # need to calculate the document_hash
        document_hash = self._embedding_generator.hash_text(
            self._serialize_json_value(documents)
        )
        return document_hash, documents

    async def transform(self, record: Gene):
        embedded_docs: list[EmbeddedGeneDocument] = []
        for section in SECTIONS.keys():
            section_document_hash, document = self._build_section_document(
                record, section
            )
            section_documents = self._chunk_document(document)
            for sdoc in section_documents:
                embedded_docs.append(
                    EmbeddedGeneDocument(
                        **sdoc.model_dump(),
                        gene_id=record.gene_id,
                        document_section=str(section),
                        document_hash=section_document_hash,
                    )
                )

        return embedded_docs

        # calculate embeddings in load so we can assemble bigger batch
        # then we get here in transform

    async def load(self, session, documents: list[EmbeddedGeneDocument]):

        embeddable_text = [d.chunk_text for d in documents]
        chunks = chunker(embeddable_text, self._params.embedding_batch_size)
        embeddings = []
        for chunk in chunks:
            embeddings.extend(self._embedding_generator.generate(chunk, as_list=False))
            self._embedded_doc_count += len(chunk)
            self.logger.info(
                f"Calcualted embeddings for {self._embedded_doc_count} documents."
            )

        edoc: EmbeddedGeneDocument
        for index, edoc in enumerate(documents):
            edoc.embedding = embeddings[index].tolist()

        chunk_metadata = [
            ChunkMetadata(
                table_id=self._table_ref.table_id,
                row_id=document.gene_id,
                document_type=str(RAGDocType.GENE),
                document_section=document.document_section,
                document_hash=document.document_hash,
                chunk_hash=document.chunk_hash,
                chunk_text=document.chunk_text,
                chunk_index=document.chunk_index,
                start_offset=document.offset_start,
                end_offset=document.offset_end,
                run_id=self.run_id,
            )
            for document in documents
        ]
        await ChunkMetadata.submit_many(session, chunk_metadata)

        chunk_embeddings = [
            ChunkEmbedding(
                chunk_metadata_id=metadata.chunk_metadata_id,
                chunk_hash=metadata.chunk_hash,
                embedding_model=str(self._params.embedding_model),
                embedding=document.embedding,
                embedding_date=datetime.now().isoformat(),
                embedding_run_id=self.run_id,
                run_id=self.run_id,
            )
            for metadata, document in zip(chunk_metadata, documents)
        ]
        await ChunkEmbedding.submit_many(session, chunk_embeddings)

        return self.create_checkpoint(record=documents[-1])

    def get_record_id(self, record: EmbeddedGeneDocument) -> str:
        return str(record.gene_id)
