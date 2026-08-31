from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Union

from niagads.common.nlp.embedding.types import (
    Embedding,
    EmbeddingBatch,
    EmbeddingFunction,
)
from niagads.common.search.models.record import SearchResultRecord
from niagads.common.search.types import MatchType
from niagads.database.helpers import datetime_column
from niagads.database.mixins import ModelDumpMixin
from niagads.database.mixins.transactions import TransactionTableMixin
from sqlalchemy import exists, inspect, literal, select
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import Mapped


class HousekeepingMixin:
    """
    Mixin providing common housekeeping fields for database models:
    - run_id: Foreign key to Core.ETLRun table
    - modification_date: Timestamp of last modification
    - is_private: Boolean flag for privacy
    """

    from niagads.database.genomicsdb.schema.admin.helpers import etlrun_fk_column

    run_id: Mapped[int] = etlrun_fk_column()
    creation_date: Mapped[datetime] = datetime_column()
    modification_date: Mapped[datetime] = datetime_column()
    # is_private: Mapped[bool] = mapped_column(nullable=True, index=True)

    @classmethod
    def columns(cls):
        """
        Return a set of all public, non-callable, non-dunder attributes defined on this mixin.
        """
        return {
            k
            for k, v in cls.__dict__.items()
            if not k.startswith("_") and not callable(v)
        }


class LookupTableMixin:
    __abstract__ = True
    _stable_id: str = None

    @classmethod
    def table_name(cls):
        return f"{cls._schema}.{cls.__tablename__}"

    @classmethod
    def stable_id_column(cls):
        if cls._stable_id is None:
            raise NotImplementedError(
                f"Cannot fetch stable id: {cls.__name__} does not define a '_stable_id' class attribute."
            )
        return cls._stable_id

    @classmethod
    def primary_key_column(cls):
        mapper = inspect(cls)
        if len(mapper.primary_key) > 1:
            raise NotImplementedError(
                "`find_primary_key` only supports single-column primary keys."
            )

        if len(mapper.primary_key) == 0:  # no PK in this table
            pk_column = getattr(cls, "_document_primary_key", None)
            if pk_column is None:
                raise NotImplementedError(
                    "Attempting to do a primary key search on a materialized view or"
                    "malformed table without a primary key."
                    "If attempting to query a RAG document please update the SQLAlchemy "
                    "model to set `_document_primary_key`."
                )
        else:
            pk_column = mapper.primary_key[0].name

        return pk_column

    @classmethod
    async def record_exists(
        cls, session: AsyncSession, filters: Dict[str, Any]
    ) -> bool:
        """
        Check if a record exists in the table based on filter criteria.

        Args:
            session (AsyncSession): SQLAlchemy async session.
            filters (Dict[str, Any]): Dictionary of field-value pairs to filter records.

        Returns:
            bool: True if a matching record exists, False otherwise.
        """
        stmt = select(
            exists().where(*(getattr(cls, k) == v for k, v in filters.items()))
        )
        result = await session.execute(stmt)
        return result.scalar() is True

    async def exists(
        self, session: AsyncSession, match_stable_id_only: bool = False
    ) -> bool:
        """
        Instance method to check if an instantiated record exists in the table.

        Args:
            session (AsyncSession): SQLAlchemy async session.

        Returns:
            bool: True if a matching record exists, False otherwise.
        """
        if match_stable_id_only:
            stable_id_field = self.__class__.stable_id_column()
            filters = {stable_id_field: getattr(self, stable_id_field)}
        else:
            filters = {}
            housekeeping_fields = HousekeepingMixin.columns()
            for field_name, value in self.model_dump().items():
                if value is not None and field_name not in housekeeping_fields:
                    filters[field_name] = value

        return await self.record_exists(session, filters)

    @classmethod
    async def find_primary_key(
        cls,
        session: AsyncSession,
        filters: Dict[str, Any],
        allow_multiple: bool = False,
    ) -> Union[int, str, list]:
        """
        Return the primary key value(s) for records matching given filter criteria.

        If the mapped class does not define a primary key (e.g., for a materialized
        view or document), this method will use the class attribute
        `_document_primary_key` if it is set. Otherwise, a NotImplementedError is
        raised.

        Args:
            session (AsyncSession): SQLAlchemy async session.
            filters (Dict[str, Any]): Dictionary of field-value pairs to filter
                records.
            allow_multiple (bool): If True, return a list of all matching PKs;
                if False, raise MultipleResultsFound on multiple matches.

        Returns:
            int, str, or list: The primary key value if exactly one match is
                found, or a list of PKs if allow_multiple is True and multiple
                matches are found.

        Raises:
            NotImplementedError: If the primary key is not a single column or
                if no primary key is defined and `_document_primary_key` is not set.
            NoResultFound: If no record matches the filter criteria.
            MultipleResultsFound: If multiple records match the filter criteria
                and allow_multiple is False.

        Example:
            await Model.find_primary_key(session, {"field1": value1})
        """
        pk_col = cls.primary_key_column()
        stmt = select(getattr(cls, pk_col)).where(
            *(getattr(cls, k) == v for k, v in filters.items())
        )
        result = await session.execute(stmt)
        records = result.scalars().all()
        if not records:
            raise NoResultFound(f"No record found for {filters} in {cls.table_name()}")
        if len(records) > 1:
            if allow_multiple:
                return records
            else:
                raise MultipleResultsFound(
                    f"Multiple records found for {filters} in {cls.table_name()}"
                )
        return records[0]

    async def retrieve_primary_key(
        self, session: AsyncSession, match_stable_id_only: bool = False
    ) -> bool:
        """
        Set the primary key value of this instance if it exists in the database.

        Args:
            session (AsyncSession): SQLAlchemy async session.

        Returns:
            bool: True if the primary key was set, False if no record found.

        Raises:
            MultipleResultsFound: If multiple records match this instance's fields.
        """
        if match_stable_id_only:
            stable_id_field = self.__class__.stable_id_column()
            filters = {stable_id_field: getattr(self, stable_id_field)}
        else:
            filters = {}
            housekeeping_fields = HousekeepingMixin.columns()
            for field_name in self.model_dump().keys():
                value = getattr(self, field_name, None)
                if value is not None and field_name not in housekeeping_fields:
                    filters[field_name] = value

        try:
            primary_key = await self.find_primary_key(
                session, filters, allow_multiple=False
            )
        except NoResultFound:
            return False

        pk_field = self.__class__.primary_key_column()
        setattr(self, pk_field, primary_key)
        return True

    @classmethod
    async def find_stable_id(
        cls,
        session: AsyncSession,
        filters: Dict[str, Any],
        allow_multiple: bool = False,
    ) -> Union[str, list]:
        """
        Return the stable identifier value(s) for records matching given filter criteria.

        The stable identifier field is defined by the model's `_stable_id` attribute.

        Args:
            session (AsyncSession): SQLAlchemy async session.
            filters (Dict[str, Any]): Dictionary of field-value pairs to filter
                records.
            allow_multiple (bool): If True, return a list of all matching stable
                IDs; if False, raise MultipleResultsFound on multiple matches.

        Returns:
            str or list: The stable identifier value if exactly one match is
                found, or a list of stable IDs if allow_multiple is True and
                multiple matches are found.

        Raises:
            NotImplementedError: If the model does not define a '_stable_id' class
                attribute.
            NoResultFound: If no record matches the filter criteria.
            MultipleResultsFound: If multiple records match the filter criteria
                and allow_multiple is False.

        Example:
            await Model.find_stable_id(session, {"field1": value1})
        """
        stable_id_field = cls.stable_id_column()
        stmt = select(getattr(cls, stable_id_field)).where(
            *(getattr(cls, k) == v for k, v in filters.items())
        )
        result = await session.execute(stmt)
        records = result.scalars().all()
        if not records:
            raise NoResultFound(f"No record found for {filters} in {cls.table_name()}")
        if len(records) > 1:
            if allow_multiple:
                return records
            else:
                raise MultipleResultsFound(
                    f"Multiple records found for {filters} in {cls.table_name()}"
                )
        return records[0]

    @classmethod
    async def fetch_record(
        cls,
        session: AsyncSession,
        filters: Dict[str, Any],
        allow_multiple: bool = False,
    ) -> Union[object, list]:
        """
        Return the full record(s) for records matching given filter criteria.

        Args:
            session (AsyncSession): SQLAlchemy async session.
            filters (Dict[str, Any]): Dictionary of field-value pairs to filter
                records.
            allow_multiple (bool): If True, return a list of all matching records;
                if False, raise MultipleResultsFound on multiple matches.

        Returns:
            object or list: The record object if exactly one match is found, or a
                list of record objects if allow_multiple is True and multiple matches
                are found.

        Raises:
            NoResultFound: If no record matches the filter criteria.
            MultipleResultsFound: If multiple records match the filter criteria
                and allow_multiple is False.

        Example:
            await Model.find_record(session, {"field1": value1})
            await Model.find_record(session, {"field1": value1}, allow_multiple=True)
        """
        stmt = select(cls).where(*(getattr(cls, k) == v for k, v in filters.items()))
        result = await session.execute(stmt)
        records = result.scalars().all()
        if not records:
            raise NoResultFound(f"No record found for {filters} in {cls.table_name()}")
        if len(records) > 1:
            if allow_multiple:
                return records
            else:
                raise MultipleResultsFound(
                    f"Multiple records found for {filters} in {cls.table_name()}"
                )
        return records[0]


class IdAliasMixin:
    """
    Mixin that provides a generic `id` property for mapped classes to facilitate
    mapping query resuts to Pydantic models (e.g., for the API)

    - If the class defines a `_stable_id` attribute (the name of a field/column),
        `id` returns the value of that field.
    - Otherwise, `id` returns the value of the primary key column (only supports
        single-column primary keys).
    """

    @property
    def id(self):
        # If the class has a '_stable_id' property/column, return that
        stable_id_field = getattr(self.__class__, "_stable_id", None)
        if stable_id_field is not None:
            return getattr(self, stable_id_field)
        # Otherwise, return the primary key value
        mapper = inspect(self.__class__)
        if len(mapper.primary_key) != 1:
            raise NotImplementedError(
                "IdAliasMixin only supports single-column primary keys."
            )
        pk_attr = mapper.primary_key[0].name
        return getattr(self, pk_attr)


class GenomicsDBTableMixin(
    ModelDumpMixin,
    LookupTableMixin,
    TransactionTableMixin,
    HousekeepingMixin,
):
    __abstract__ = True


class GenomicsDBMVMixin(ModelDumpMixin, LookupTableMixin):
    _document_primary_key = None  # set to do pk lookups on RAG docs
    __abstract__ = True


class SearchMixin(ABC):

    @classmethod
    def _build_match_cte(
        cls,
        name: str,
        match_type: MatchType,
        matched_text_expr,
        where_condition,
        score: float = 1.0,
        join_clause=None,
        post_action: Optional[callable] = None,
    ):
        """Build a standardized SQLAlchemy SELECT statement for search context.

        Constructs a select query that includes standard match metadata (type, rank,
        score) along with the matched text. Handles optional joins for complex queries.

        Args:
            name (str): cte name - necessary for debugging purposes
            match_type (MatchType): The match type enum value determining rank priority.
            matched_text_expr (ColumnElement): SQLAlchemy column expression for the matched
                text. Can be a simple column (e.g., OntologyTerm.term) or complex expression
                (e.g., case() statement).
            where_condition (ColumnElement): SQLAlchemy boolean column expression for
                filtering records. Combined with AND conditions as appropriate to the
                search context.
            score (Union[float, ColumnElement], optional): Match score value. Can be a
                literal float (e.g., 1.0 for exact matches) or a dynamic expression
                (e.g., func.similarity(...) for fuzzy matches). Defaults to 1.0.
            join_clause (Optional[tuple], optional): Tuple of (table, condition) for
                joining an additional table to the base select. Used for queries
                requiring lateral joins or derived tables. Defaults to None (no join).
            post_action (Optional): additional expressions (applied using lambda function)
                to further filter or revise result (e.g., .where or .distinct)

        Returns:
            Select: A SQLAlchemy Select statement with columns for the ORM object,
                match_type, rank, score, and matched_text, filtered by the where_condition.

        Example:
            see components/niagads/database/genomicsdb/schema/reference/ontology.py
        """
        stmt = select(
            cls,
            literal(str(match_type)).label("match_type"),
            literal(match_type.rank()).label("rank"),
            literal(score).label("score"),
            matched_text_expr.label("matched_text"),
        )
        if join_clause:
            stmt = stmt.join(*join_clause)  # unpacks (table, condition) tuple

        stmt.where(where_condition)

        if post_action:
            stmt = post_action(stmt)

        return stmt.cte(name)

    @classmethod
    @abstractmethod
    async def search(
        cls, session: AsyncSession, search_text: str, allow_fuzzy: bool = False
    ) -> list[SearchResultRecord]:
        """Search for records using deterministic text matching.

        Args:
            session (AsyncSession): Active asynchronous database session.
            search_text (str): Text phrase to search for.
        Returns:
            Matching search result records.  Returns an empty list if no matches are found
        """
        ...

    @classmethod
    @abstractmethod
    async def semantic_search(
        cls,
        session: AsyncSession,
        search_text: str,
        embed: EmbeddingFunction,
        *,
        limit=10,
    ) -> list[SearchResultRecord]:
        """Search for semantically similar records using embedded query text.

        Args:
            session (AsyncSession): Active asynchronous database session.
            search_text: Text phrase to embed and use for semantic search.
            embed (callable): Function used to generate embeddings, must match EmbeddingFunction protocol.
            limit (int): Maximum number of results to return.

        Returns:
            Search result records ranked by semantic similarity. Returns an empty list if no matches are found
        """
        ...

    @classmethod
    @abstractmethod
    async def semantic_search_by_embedding(
        cls,
        session: AsyncSession,
        phrase: list[str],
        embedding: Embedding,
        *,
        limit=10,
    ) -> list[SearchResultRecord]:
        """Search for semantically similar records using precomputed embeddings.

        Args:
            session (AsyncSession): Active asynchronous database session.
            phrase (str): Text phrase associated with the supplied embeddings.
            embedding (Embedding): Precomputed embedding corresponding to the input phrase.
            limit (int): Maximum number of results to return.

        Returns:
            Search result records ranked by semantic similarity.
        """
        ...
