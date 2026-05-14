from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.admin.types import TableRef
from niagads.database.genomicsdb.schema.reference.externaldb import ExternalDatabase
from niagads.nlp.embeddings import TextEmbeddingGenerator
from pydantic import BaseModel


class ExternalDatabaseContextMixin(BaseModel):
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

    _external_database: ExternalDatabase

    @property
    def external_database_id(self):
        return self._external_database.external_database_id

    async def on_run_start(self, session):
        if self.is_etl_run:
            self.__external_database = await self._params.fetch_xdbref(session)


class EmbeddingGeneratorContextMixin(BaseModel):
    """
    Mixin for ETL plugins to provide context and setup for text embedding generation.

    This mixin manages the embedding generator and table reference context for plugins that require
    text embedding functionality. It initializes the embedding generator on run start and provides
    batch size warnings based on hardware detection.

    Attributes:
        _table_ref (TableRef): Reference to the target table for embeddings.
        _embedding_generator (TextEmbeddingGenerator): The embedding generator instance.

    Methods:
        set_table_ref: Async method to set the table reference from a model.
        on_run_start: Async hook to initialize the embedding generator and log batch size warnings.
    """

    _table_ref: TableRef = None

    async def set_table_ref(self, session, table_model):
        self._table_ref = await TableCatalog.get_table_ref(session, table_model)

    async def on_run_start(self, session):
        """on run start hook override"""
        self._embedding_generator = TextEmbeddingGenerator(self._params.embedding_model)
        if self._embedding_generator.is_cpu_limited:
            if self._params.embedding_batch_size > 128:
                self.logger.warning(
                    "CPU detected; batch sizes > 128 may cause slowdowns or high memory use when calculating embeddings."
                )
        elif self._params.embedding_batch_size > 512:
            self.logger.warning(
                "GPU detected; batch sizes > 512 may cause slowdowns or high memory use when calculating embeddings."
            )
