"""Generate and load semantic chunk embeddings for gene documents."""

import json

from niagads.common.types import ETLOperation
from niagads.database.genomicsdb.schema.gene.documents import Gene
from niagads.database.genomicsdb.schema.ragdoc.chunks import (
    ChunkEmbedding,
    ChunkMetadata,
)

from niagads.database.genomicsdb.schema.ragdoc.types import GeneDocumentSection
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.mixins import EmbeddingGeneratorContextMixin
from niagads.etl.plugins.parameters import BasePluginParams, EmbeddingParameterMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLLoadStrategy
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


class GeneDocumentEmbeddingParams(BasePluginParams, EmbeddingParameterMixin):
    """Parameters for loading embeddings from the gene document view."""

    ...


@PluginRegistry.register(
    metadata=PluginMetadata(
        version="1.0",
        description=(
            "Load gene document embeddings grouped by identity, structure, "
            "annotation, and references. Skip unchanged chunks for the selected "
            "model; retain previous chunk versions."
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

    async def on_run_start(self, session) -> None:
        await EmbeddingGeneratorContextMixin.on_run_start(self, session)
        if self.is_etl_run:
            await self.set_table_ref(self, session, Gene)

            stmt = select(Gene)
            self._gene_records = (await session.execute(stmt)).scalars().all()
            self.logger.info(f"Retrieved {len(self._gene_records)} gene documents.")

    def extract(self):
        for record in self._gene_records:
            yield record

    def _generate_chunk_text(self, obj):
        chunk_text = json.dumps(obj)

    def _build_document(self, record: Gene, section: GeneDocumentSection) -> str:
        """Build the complete JSON text for a gene document section."""
        document = {
            field: value
            for field in SECTIONS[section]
            if (value := getattr(record, field)) is not None
        }

        return json.dumps(document, sort_keys=True, separators=(",", ":"))

    async def transform(self, record: Gene):
        for section in SECTIONS.keys():
            self._build_document(self, record, section)

    async def load(self, session, transformed):
        return await super().load(session, transformed)
