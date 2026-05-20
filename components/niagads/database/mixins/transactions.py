import json
from datetime import datetime
from typing import Self

from niagads.common.models.types import Range
from niagads.database.decorators import CompressedJson, RangeType
from niagads.utils.string import xstr
from sqlalchemy import ARRAY, exists, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.dialects.postgresql import JSON, JSONB
from sqlalchemy_utils.types.ltree import Ltree


class TransactionTableMixin(DeclarativeBase):
    __abstract__ = True

    @classmethod
    def table_name(cls):
        return f"{cls._schema}.{cls.__tablename__}"

    @classmethod
    def primary_key_column(cls):
        return cls.__mapper__.primary_key[0].name

    async def stage(self, session: AsyncSession):
        """
        Insert this table entry into the database but don't flush, just stage the addition.

        Args:
            session (AsyncSession): SQLAlchemy Async Session
        """
        session.add(self)

    async def submit(self, session: AsyncSession) -> int:
        """
        Insert this table entry into the database and return the primary key value.

        Args:
            session: SQLAlchemy AsyncSession.


        Returns:
            int: The primary key value of the inserted record.
        """
        session.add(self)
        await session.flush()

        pk_name = self.__mapper__.primary_key[0].name
        return getattr(self, pk_name)

    @classmethod
    def verify_record_type(cls, records: list[Self]):
        for record in records:
            if not isinstance(record, cls):
                raise TypeError(
                    f"expected instances of {cls.__name__}; "
                    f"got {type(record).__name__}"
                )

    @classmethod
    async def submit_many(cls, session: AsyncSession, records: list[Self]):
        """batch insert tables into the database"""
        if not records:
            raise ValueError("Record list is empty; nothing to submit")

        cls.verify_record_type(records)
        session.add_all(records)
        await session.flush()

    @classmethod
    async def detach_many(cls, session: AsyncSession, records: list[Self]):
        """
        Expunge list of instances from the SQLAlchmey session; serves mainly to lower
        session memory usage and identity mapping overhead as flushes increase
        """
        if not records:
            raise ValueError("Record list is empty; nothing to detach")

        cls.verify_record_type(records)
        await session.flush()
        for record in records:
            session.expunge(record)

    async def detach(self, session: AsyncSession):
        """
        Expunge this instance from the SQLAlchemy session so that all currently loaded attributes
        remain accessible after the session is closed. This prevents DetachedInstanceError when
        accessing attributes that were loaded before expunging, but disables lazy loading of any
        unloaded attributes.

        Args:
            session (AsyncSession): The SQLAlchemy async session from which to expunge this instance.
        """
        await session.flush()
        session.expunge(self)

    async def update(self, session: AsyncSession):
        """
        Update this table entry in the database. Must include primary key.

        Args:
            session: SQLAlchemy AsyncSession.

        Raises:
            ValueError: If the primary key field is not set in this instance
            or the row does not exist in the database.
        """
        pk_name = self.__mapper__.primary_key[0].name
        pk_value = getattr(self, pk_name, None)
        if pk_value is None:
            raise ValueError(
                f"Primary key field '{pk_name}' must be set to update a record in the database."
            )

        stmt = select(exists().where(getattr(type(self), pk_name) == pk_value))
        result = await session.execute(stmt)
        if not result.scalar():
            raise ValueError(
                f"Cannot update record; no row exists in the database with {pk_name}={pk_value}"
            )

        if hasattr(self, "modification_date"):
            self.modification_date = datetime.now().isoformat()

        await session.merge(self)
        await session.flush()

    @classmethod
    async def get_run_transaction_count(
        cls,
        session: AsyncSession,
        run_id: int,
        run_id_field: str = "run_id",
        estimate_only: bool = False,
    ) -> int:
        """
        Return the count of records in this table matching the given run_id.
        If estimate_only is True, use estimate_row_count instead.
        Args:
            session (AsyncSession): SQLAlchemy async session.
            run_id (int): The run_id to filter by.
            run_id_field (str): The field name to use for run_id (default 'run_id').
            estimate_only (bool): If True, use estimate_row_count.
        Returns:
            int: Count of matching records.
        """
        if run_id_field not in cls.__table__.columns:
            raise NotImplementedError(
                "Transaction counting requires existence of a field "
                f"(expecting a {run_id_field} - field name can be customized) "
                "that stores the run_id so that run transactions can be tallied."
            )
        if estimate_only:
            qualified_table_name = f"{cls.__table__.schema}.{cls.__table__.name}"
            query = f"'SELECT * FROM {qualified_table_name} WHERE {run_id_field} = {run_id}'"
            try:
                stmt = select(func.estimate_row_count(query))
                result = await session.execute(stmt)
            except ProgrammingError:
                raise NotImplementedError(
                    "Cannot estimate counts: `estimate_row_count` function not defined."
                )
            return result.scalar_one()

        stmt = select(cls).where(getattr(cls, run_id_field) == run_id)
        result = await session.execute(stmt)
        return result.scalars().count()

    @staticmethod
    def __record_value_to_string(value: any, col_type=None):
        """
        Convert a value to its string representation for COPY bulk loading, handling custom and PostgreSQL types.

        Args:
            value (any): The value to convert.
            col_type: The SQLAlchemy column type or custom decorator.

        Returns:
            str: The string representation of the value, suitable for COPY input.

        Handles:
            - RangeType: Converts to PostgreSQL range string.
            - CompressedJson: Serializes and hex-encodes compressed JSON.
            - Ltree: Converts to string.
            - JSON, JSONB, ARRAY: Serializes to JSON string.
            - dict/list: Serializes to JSON string if not empty, else NULL.
            - None: Returns 'NULL'.
        """

        if value is not None:
            if isinstance(col_type, RangeType):
                value: Range
                return value.to_range_string()
            if isinstance(col_type, CompressedJson):
                compressed_value = col_type.process_bind_param(value, None)
                return "\\x" + compressed_value.hex()
            if isinstance(col_type, Ltree):
                return str(value)
            if isinstance(col_type, (JSON, JSONB, ARRAY)):
                return json.dumps(value)
            if isinstance(value, (dict, list)):
                if len(value) == 0:
                    value = None
                else:
                    return json.dumps(value)
            if isinstance(value, Ltree):
                return str(value)

        return xstr(value, null_str="NULL")

    @classmethod
    async def copy(cls, session: AsyncSession, records: list[Self]):
        """
        Batch insert records using PostgreSQL COPY for high performance.

        Args:
            session (AsyncSession): SQLAlchemy async session.
            records (list[Self]): Records to insert.

        Raises:
            ValueError: If records list is empty.
            TypeError: If records contain unexpected types.
        """
        if not records:
            raise ValueError("Record list is empty; nothing to submit")

        cls.verify_record_type(records)

        excluded_columns = [
            cls.primary_key_column(),
            "creation_date",
            "modification_date",
        ]

        # Get column metadata
        mapper = inspect(cls)
        columns = mapper.columns
        column_names = [c.name for c in columns if c.name not in excluded_columns]

        # Build pipe-delimited buffer
        async def byte_generator():
            for record in records:
                row = []
                for col_name in column_names:
                    value = getattr(record, col_name, None)
                    col_type = columns[col_name].type

                    str_value = cls.__record_value_to_string(value, col_type)
                    row.append(str_value)

                yield ("|".join(row) + "\n").encode("utf-8")

        schema_name, table_name = cls.table_name().split(".")

        # Execute COPY via raw connection
        session_connection = await session.connection()
        sqlalchemy_proxy_connection = await session_connection.get_raw_connection()
        asyncpg_raw_connection = sqlalchemy_proxy_connection.driver_connection

        await asyncpg_raw_connection.copy_to_table(
            table_name,
            schema_name=schema_name,
            columns=column_names,
            source=byte_generator(),
            format="text",
            delimiter="|",
            null="NULL",
        )
