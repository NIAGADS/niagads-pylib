from niagads.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.genomicsdb.schema.admin.helpers import table_fk_column
from niagads.genomicsdb.schema.registry import SchemaRegistry
from sqlalchemy import Integer, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column


class TableRefMixin:
    """
    Mixin for tables that have a table_id/row_id mapping to the table catalog.
    """

    __abstract__ = True
    _table_ref: TableCatalog = None

    table_id: Mapped[int] = table_fk_column()
    row_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    async def fetch_table_ref(self, session: AsyncSession):
        """
        Fetches the TableCatalog entry for this object's table_id.

        Args:
            session (AsyncSession): SQLAlchemy async session.

        Raises:
            sqlalchemy.exc.NoResultFound: If no entry is found for table_id.
        """
        result = await session.execute(
            select(TableCatalog).where(TableCatalog.table_id == self.table_id)
        )
        self._table_ref = result.scalar_one()  # will raise error if not found

    async def get_table_name(self, session: AsyncSession = None):
        """
        Returns the fully qualified table name for the mapped table.

        Args:
            session (AsyncSession, optional): SQLAlchemy async session.

        Returns:
            str: The schema.table name.
        """
        if not self._table_ref:
            await self.fetch_table_ref(session)
        return self._table_ref.full_name()

    async def get_table_pk_field(self, session: AsyncSession = None):
        """
        Returns the primary key field name for this object's table.

        Args:
            session (AsyncSession, optional): SQLAlchemy async session.

        Returns:
            str: The primary key field name.
        """
        if not self._table_ref:
            await self.fetch_table_ref(session)
        return self._table_ref.table_primary_key

    def get_table_model(self, session: AsyncSession):
        schema, table = self.get_table_name(session).split(".")

        registry = type(self).registry

        for mapper in registry.mappers:
            tbl = mapper.local_table
            if tbl.name == table and tbl.schema == schema:
                return mapper.class_

        raise LookupError(f"{self._table_ref.full_name()} not mapped")
