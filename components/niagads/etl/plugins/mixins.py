import json
from typing import Iterator, Optional

from niagads.common.models.base import CustomBaseModel
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.admin.types import TableRef
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.nlp.embeddings import TextEmbeddingGenerator
from niagads.utils.string import truncate_tokens


class DocumentChunk(CustomBaseModel):
    chunk_text: str
    chunk_index: Optional[int] = None
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None


class ExternalDatabaseContextMixin:
    """
    Mixin for AbstractBasePlugin classes to provide context and validation for external database references.

    This mixin manages the external database context for ETL plugins, exposing the external database ID and
    ensuring the reference is fetched and available at ETL run start.

    Attributes:
        _external_database (ExternalDatabase): The external database reference object.

    Methods:
        external_database_id: Returns the external database ID.
        on_run_start: Async hook to fetch and set the external database reference at ETL run start.
    """

    _external_database: ExternalDatabase = None

    @property
    def external_database_id(self):
        return self._external_database.external_database_id if self.is_etl_run else None

    async def on_run_start(self, session):
        if self.is_etl_run:
            self._external_database = await self._params.fetch_xdbref(session)


class EmbeddingGeneratorContextMixin:
    """
    Mixin for ETL plugins to provide context and setup for text embedding generation.

    This mixin manages the embedding generator and table reference context for plugins that require
    text embedding functionality. It initializes the embedding generator on run start and provides
    token-aware document chunking and batch size warnings based on hardware detection.

    Attributes:
        _table_ref (TableRef): Reference to the target table for embeddings.
        _embedding_generator (TextEmbeddingGenerator): The embedding generator instance.

    Methods:
        set_table_ref: Async method to set the table reference from a model.
        on_run_start: Async hook to initialize the embedding generator and log batch size warnings.
        chunk_text: Hook for plugin-specific non-JSON text parsing.
    """

    __HARD_TOKEN_MARGIN = 20

    _table_ref: TableRef = None
    _embedding_generator: TextEmbeddingGenerator = None
    _hard_token_limit: int = None

    @property
    def soft_token_limit(self):
        return self._params.soft_token_limit

    async def set_table_ref(self, session, table_model):
        self._table_ref = await TableCatalog.get_table_ref(session, table_model)

    async def on_run_start(self, session):
        """on run start hook override"""
        self._embedding_generator = TextEmbeddingGenerator(
            self._params.embedding_model, force_cpu=self._params.embedding_force_cpu
        )
        self._hard_token_limit = (
            self._embedding_generator.max_sequence_length - self.__HARD_TOKEN_MARGIN
        )
        if self._embedding_generator.is_cpu_limited:
            if self._params.embedding_batch_size > 128:
                self.logger.warning(
                    "CPU detected; batch sizes > 128 may cause slowdowns or high memory use when calculating embeddings."
                )
        elif self._params.embedding_batch_size > 512:
            self.logger.warning(
                "GPU detected; batch sizes > 512 may cause slowdowns or high memory use when calculating embeddings."
            )

    def _chunk_list(self, keyed_list, index: int):
        """Split a large JSON list into model-sized chunks.

        Args:
            keyed_list (dict): A single-key dictionary containing the list to chunk.
            index (int): Index preceding the first generated chunk.

        Yields:
            DocumentChunk: A chunk containing a subset of the list values.
        """
        key, list_values = next(iter(keyed_list.items()))
        current_chunk = []
        empty_chunk_token_count = self._embedding_generator.token_count(
            self._serialize_json_value({key: []})
        )
        current_token_count = empty_chunk_token_count
        next_index = 0 if index is None else index + 1

        for value in list_values:
            value_token_count = self._embedding_generator.token_count(
                self._serialize_json_value(value)
            )
            if isinstance(value, str) and value_token_count > self.SOFT_TOKEN_LIMIT:
                value = truncate_tokens(
                    value,
                    self._embedding_generator.tokenizer,
                    self.SOFT_TOKEN_LIMIT,
                )
                value_token_count = self._embedding_generator.token_count(
                    self._serialize_json_value(value)
                )
            if (
                current_chunk
                and current_token_count + value_token_count > self._hard_token_limit
            ):
                yield DocumentChunk(
                    chunk_text=self._serialize_json_value({key: current_chunk}),
                    chunk_index=next_index,
                )
                next_index += 1
                current_chunk = []
                current_token_count = empty_chunk_token_count

            current_chunk.append(value)
            current_token_count += value_token_count

        if current_chunk:
            yield DocumentChunk(
                chunk_text=self._serialize_json_value({key: current_chunk}),
                chunk_index=next_index,
            )

    def _chunk_json_value(self, value, index: int = None):
        """Split a JSON object into model-sized chunks.

        Args:
            value (dict): JSON object to split into chunks.
            index (int, optional): Index preceding the first generated chunk.

        Yields:
            DocumentChunk: A model-sized JSON chunk.

        Raises:
            ValueError: If a nested dictionary exceeds the hard token limit.
        """
        json_str = self._serialize_json_value(value)
        token_count = self._embedding_generator.token_count(json_str)

        if token_count <= self.SOFT_TOKEN_LIMIT:
            yield DocumentChunk(
                chunk_text=json_str,
                chunk_index=index,
            )
            return

        current_chunk = {}
        current_token_count = 0
        next_index = 0 if index is None else index + 1
        oversized_items = []

        for key, child_value in value.items():
            item = {key: child_value}
            item_token_count = self._embedding_generator.token_count(
                self._serialize_json_value(item)
            )

            if item_token_count > self._hard_token_limit:
                oversized_items.append(item)
                continue

            if (
                current_chunk
                and current_token_count + item_token_count > self.SOFT_TOKEN_LIMIT
            ):
                yield DocumentChunk(
                    chunk_text=self._serialize_json_value(current_chunk),
                    chunk_index=next_index,
                )
                next_index += 1
                current_chunk = item
                current_token_count = item_token_count
            else:
                current_chunk.update(item)
                current_token_count += item_token_count

        if current_chunk:
            yield DocumentChunk(
                chunk_text=self._serialize_json_value(current_chunk),
                chunk_index=next_index,
            )
            next_index += 1

        for oversized_item in oversized_items:
            value = next(iter(oversized_item.values()))
            if isinstance(value, str):
                yield DocumentChunk(
                    chunk_text=self._serialize_json_value(oversized_item),
                    chunk_index=next_index,
                )
                next_index += 1
            if isinstance(value, dict):
                raise ValueError(f"oversized nested dict: {value}")
            if isinstance(value, list):
                for chunk in self._chunk_list(oversized_item, next_index):
                    yield chunk
                    next_index = chunk.chunk_index + 1

    def _chunk_document(self, document: str | dict) -> Iterator[DocumentChunk]:
        """Parse and split a JSON document into model-sized chunks.

        Args:
            document (str | dict): JSON text, or a parsed JSON object, to split.

        Returns:
            Iterator[DocumentChunk]: Chunks produced from the document.

        Raises:
            TypeError: If ``document`` is not a string or dictionary.
        """
        if isinstance(document, dict):
            return self._chunk_json_value(document)

        if not isinstance(document, str):
            raise TypeError("document must be a string or dictionary")

        try:
            return self._chunk_json_value(json.loads(document))
        except json.JSONDecodeError:
            return self._chunk_text(document)

    def _serialize_json_value(self, value) -> str:
        """Serialize a JSON value compactly for storage and token counting."""

        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _chunk_text(self, document: str) -> Iterator[DocumentChunk]:
        """Convert a non-JSON document into model-sized chunks.

        Args:
            document (str): Non-JSON document to split.

        Returns:
            Iterator[DocumentChunk]: Chunks produced from the document.

        Raises:
            NotImplementedError: When the embedding plugin does not implement
                text-specific chunking.
        """
        raise NotImplementedError(
            "Text chunking must be implemented by the embedding plugin."
        )
