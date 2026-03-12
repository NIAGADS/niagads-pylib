from datetime import datetime
from typing import Any, Dict, Union

from niagads.database.helpers import datetime_column
from niagads.database.mixins import ModelDumpMixin
from niagads.database.mixins.transactions import TransactionTableMixin
from sqlalchemy import exists, inspect, select
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped

class HousekeepingMixin:
    """
    Mixin providing common housekeeping fields for database models:
    - run_id: Foreign key to Core.ETLRun table
    - modification_date: Timestamp of last modification
    - is_private: Boolean flag for privacy
    """

    from niagads.genomicsdb.schema.admin.helpers import etlrun_fk_column

    run_id: Mapped[int] = etlrun_fk_column()
    creation_date: Mapped[datetime] = datetime_column()
    modification_date: Mapped[datetime] = datetime_column()
    # is_private: Mapped[bool] = mapped_column(nullable=True, index=True)

    def get_model_fields(self):
        """
        Return a dictionary of all public, non-callable attributes for this instance.
        Excludes dunder, private, and callable attributes.
        """
        return {
            k: v
            for k, v in self.__dict__.items()
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
            housekeeping_fields = HousekeepingMixin.get_model_fields()
            for field_name in self.model_dump().keys():
                value = getattr(self, field_name, None)
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
        rows = result.all()
        if not rows:
            raise NoResultFound(f"No record found for {filters} in {cls.table_name()}")
        if len(rows) > 1:
            if allow_multiple:
                return [row[0] for row in rows]
            else:
                raise MultipleResultsFound(
                    f"Multiple records found for {filters} in {cls.table_name()}"
                )
        return rows[0][0]

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
            housekeeping_fields = HousekeepingMixin.get_model_fields()
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
        rows = result.all()
        if not rows:
            raise NoResultFound(f"No record found for {filters} in {cls.table_name()}")
        if len(rows) > 1:
            if allow_multiple:
                return [row[0] for row in rows]
            else:
                raise MultipleResultsFound(
                    f"Multiple records found for {filters} in {cls.table_name()}"
                )
        return rows[0][0]

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
        rows = result.scalars().all()
        if not rows:
            raise NoResultFound(f"No record found for {filters} in {cls.table_name()}")
        if len(rows) > 1:
            if allow_multiple:
                return rows
            else:
                raise MultipleResultsFound(
                    f"Multiple records found for {filters} in {cls.table_name()}"
                )
        return rows[0]


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
