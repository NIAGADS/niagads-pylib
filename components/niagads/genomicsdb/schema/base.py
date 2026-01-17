from datetime import datetime
from typing import Any, Dict, Union

from niagads.database.mixins.serialization import ModelDumpMixin
from sqlalchemy import DATETIME, exists, func, inspect, select
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.orm import DeclarativeBase


class HousekeepingMixin(object):
    """
    Mixin providing common housekeeping fields for database models:
    - run_id: Foreign key to Core.ETLRun table
    - modification_date: Timestamp of last modification
    - is_private: Boolean flag for privacy
    """

    run_id: Mapped[int] = mapped_column(
        ForeignKey("admin.eltrun.etl_run_id"),
        nullable=False,
        index=True,
    )
    creation_date: Mapped[datetime] = mapped_column(
        DATETIME,
        server_default=func.now(),
        nullable=False,
    )
    modification_date: Mapped[datetime] = mapped_column(
        DATETIME,
        server_default=func.now(),
        nullable=False,
    )
    # is_private: Mapped[bool] = mapped_column(nullable=True, index=True)


class LookupTableMixin(
    DeclarativeBase,
    ModelDumpMixin,
):
    stable_id: str = None

    @classmethod
    def table_name(cls):
        return f"{cls.metadata.schema}.{cls.__tablename__}"

    @classmethod
    async def exists(cls, session: AsyncSession, filters: Dict[str, Any]) -> bool:
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
        `document_primary_key` if it is set. Otherwise, a NotImplementedError is
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
                if no primary key is defined and `document_primary_key` is not set.
            NoResultFound: If no record matches the filter criteria.
            MultipleResultsFound: If multiple records match the filter criteria
                and allow_multiple is False.

        Example:
            await Model.find_primary_key(session, {"field1": value1})
        """
        mapper = inspect(cls)
        if len(mapper.primary_key) > 1:
            raise NotImplementedError(
                "`find_primary_key` only supports single-column primary keys."
            )

        if len(mapper.primary_key) == 0:  # no PK in this table
            pk_col = getattr(cls, "document_primary_key", None)
            if pk_col is None:
                raise NotImplementedError(
                    "Attempting to do a primary key search on a materialized view or"
                    "malformed table without a primary key."
                    "If attempting to query a RAG document please update the SQLAlchemy "
                    "model to set `document_primary_key`."
                )
        else:
            pk_col = mapper.primary_key[0].name

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

    @classmethod
    async def find_stable_id(
        cls,
        session: AsyncSession,
        filters: Dict[str, Any],
        allow_multiple: bool = False,
    ) -> Union[str, list]:
        """
        Return the stable identifier value(s) for records matching given filter criteria.

        The stable identifier field is defined by the model's `stable_id` attribute.

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
            NotImplementedError: If the model does not define a 'stable_id' class
                attribute.
            NoResultFound: If no record matches the filter criteria.
            MultipleResultsFound: If multiple records match the filter criteria
                and allow_multiple is False.

        Example:
            await Model.find_stable_id(session, {"field1": value1})
        """
        stable_id_field = getattr(cls, "stable_id", None)
        if stable_id_field is None:
            raise NotImplementedError(
                f"Cannot fetch stable id: {cls.__name__} does not define a 'stable_id' class attribute."
            )
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
    async def find_record(
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


class DeclarativeTableBase(LookupTableMixin, HousekeepingMixin): ...


class DeclarativeMaterializedViewBase(LookupTableMixin):
    document_primary_key = None  # so we can do primary key lookups on RAG documents
