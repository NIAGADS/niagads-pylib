"""Generate and load semantic chunk embeddings for gene documents."""

import json
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, Optional

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
from niagads.utils.dict import promote_nested
from niagads.utils.list import chunker
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
    GeneDocumentSection.MEMBERSHIPS: ["memberships"],
    GeneDocumentSection.FUNCTIONAL_ANNOTATION: ["functional_annotation"],
    GeneDocumentSection.REFERENCES: ["xrefs"],
}


class EmbeddedGeneDocument(DocumentChunk):
    gene_id: int
    document_section: str
    document_hash: bytes
    chunk_hash: bytes
    embedding: Optional[list] = None  # so it can be set in batch


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
        can_resume=False,
    )
)
class GeneDocumentEmbeddingLoader(AbstractBasePlugin, EmbeddingGeneratorContextMixin):
    """Read gene documents in keyset pages and persist their chunk embeddings."""

    _params: GeneDocumentEmbeddingParams

    def __init__(
        self,
        params: Dict[str, Any],
        name: Optional[str] = None,
        log_path: str = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(params, name, log_path, debug, verbose)
        self._gene_records: list[SimpleNamespace] = None
        self._embedded_doc_count = 0

    async def on_run_start(self, session) -> None:
        await EmbeddingGeneratorContextMixin.on_run_start(self, session)
        if self.is_etl_run:
            await self.set_table_ref(session, Gene)

            self.logger.info("Fetching Gene Records")
            stmt = select(Gene)
            records = (await session.execute(stmt)).scalars().all()
            fields = {field for section in SECTIONS.values() for field in section}
            fields.add("gene_id")
            self._gene_records = [
                SimpleNamespace(**{field: getattr(record, field) for field in fields})
                for record in records
            ]
            self.logger.info(f"Retrieved {len(self._gene_records)} gene documents.")

    def extract(self):
        for index, record in enumerate(self._gene_records, start=1):
            if index % 10000 == 0:
                self.logger.info(f"Extracted {index} gene records.")
            yield record

    def _build_structure_document(self, record: Gene):
        structure = record.gene_structure or {}
        if not structure:
            raise ValueError(
                f"All genes should have at minimum a `location`. Check database for error: gene_id={record.gene_id}."
            )

        transcripts = structure.get("transcripts", None)

        exon_ids = set(
            [
                exon["id"]
                for transcript in transcripts
                for exon in transcript.get("exons", [])
            ]
        )

        document = {
            "cytogenic_location": structure.get("cytogenic_location"),
            "transcript_ids": [transcript["id"] for transcript in transcripts],
            "exon_ids": list(exon_ids),
            "protein_ids": [
                protein
                for transcript in transcripts
                for protein in transcript.get("proteins", [])
            ],
        }

        return {
            k: v
            for k, v in document.items()
            if v is not None and (not isinstance(v, (list, dict)) or v)
        }

    def _build_membership_document(self, record: Gene):
        memberships = record.memberships or {}
        if not memberships:
            return {}
        pathways = memberships.get("pathways", [])
        curated_lists = memberships.get("curated_lists", [])
        gene_families = memberships.get("gene_families", {})

        document = {
            "pathways": [
                f'{pathway["pathway_name"]} '
                f'({pathway["data_source"]}:{pathway["pathway_id"]})'
                for pathway in pathways
            ],
            "curated_lists": [
                "; ".join(
                    [
                        curated_list["listing"],
                        f'assertion: {curated_list["assertion"]}',
                        f'grouped locus: {curated_list["qualifier"]["grouped_locus"]}',
                        f'reported locus: {curated_list["qualifier"]["reported_locus"]}',
                        (
                            "evidence: "
                            f'{curated_list["evidence_code"]["term"]} '
                            f'({curated_list["evidence_code"]["curie"]})'
                        ),
                    ]
                )
                for curated_list in curated_lists
            ],
            "gene_families": [
                f"{family} ({source})"
                for source, families in gene_families.items()
                for family in families
            ],
        }

        return {key: value for key, value in document.items() if value}

    def _build_functional_annotation_document(self, record: Gene):
        annotations = record.functional_annotation or {}

        return {namespace: terms for namespace, terms in annotations.items()}

    def _build_section_document(
        self, record: Gene, section: GeneDocumentSection
    ) -> tuple[bytes, dict]:
        """Build the complete JSON text for a gene document section."""
        if section == GeneDocumentSection.STRUCTURE:
            documents = self._build_structure_document(record)
        elif section == GeneDocumentSection.MEMBERSHIPS:
            documents = self._build_membership_document(record)
        elif section == GeneDocumentSection.FUNCTIONAL_ANNOTATION:
            documents = self._build_functional_annotation_document(record)
        else:
            documents = {
                field: value
                for field in SECTIONS[section]
                if (value := getattr(record, field)) is not None
                and value is not False
                and (not isinstance(value, (list, dict)) or value)
            }

        # need to calculate the document_hash
        document_hash = self._embedding_generator.hash_text(
            self._serialize_json_value(documents)
        )
        return document_hash, documents

    async def transform(self, record: Gene):
        embedded_docs: list[EmbeddedGeneDocument] = []
        self.logger.debug(f"Transforming gene_id={record.gene_id}")

        for section in SECTIONS.keys():
            section_document_hash, document = self._build_section_document(
                record, section
            )

            if self._verbose:
                self.logger.debug(f"{record.gene_id}: {section}: {document}")

            if not document:
                continue

            section_documents = self._chunk_document(document)
            for sdoc in section_documents:
                edoc = EmbeddedGeneDocument(
                    **sdoc.model_dump(),
                    gene_id=record.gene_id,
                    document_section=str(section),
                    document_hash=section_document_hash,
                    chunk_hash=TextEmbeddingGenerator.hash_text(sdoc.chunk_text),
                )
                embedded_docs.append(edoc)

                self.logger.debug(edoc.chunk_text)

        return embedded_docs

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
