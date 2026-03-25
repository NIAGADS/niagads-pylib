from datetime import datetime
from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.exc import ProgrammingError


class TransactionTableMixin(DeclarativeBase):
    __abstract__ = True

    @classmethod
    def table_name(cls):
        return f"{cls._schema}.{cls.__tablename__}"

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
