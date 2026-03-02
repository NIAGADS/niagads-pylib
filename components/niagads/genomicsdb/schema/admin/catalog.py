from niagads.genomicsdb.schema.admin.base import AdminTableBase
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncSession


class AdminSchemaCatalog(AdminTableBase):
    """
    Catalog of database schemas.
    """

    __tablename__ = "schemacatalog"

    schema_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )


class AdminTableCatalog(AdminTableBase):
    """
    Catalog of tables within a schema.
    """

    __tablename__ = "tablecatalog"
    __table_args__ = (
        UniqueConstraint("schema_id", "name", name="uq_schema_table_name"),
    )

    table_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("admin.schemacatalog.schema_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    primary_key: Mapped[str] = mapped_column(String(50), nullable=False, index=False)

    schema_name: str

    async def table_ref(self, session: AsyncSession = None) -> str:
        """
        Returns the 'schema.table' name representation for this table.
        If the schema relationship is not loaded, fetches it from the session.

        Args:
            session: SQLAlchemy Session or AsyncSession (required if schema is not loaded)

        Returns:
            str: schema.table name
        """
        if self.schema_name is None:
            if session is None:
                raise ValueError("Session required to fetch schema if not loaded.")

            result = await session.execute(
                select(AdminSchemaCatalog.name).where(
                    AdminSchemaCatalog.schema_id == self.schema_id
                )
            )
            self.schema_name = result.scalar_one_or_none()
            if self.schema_name is None:
                raise ValueError(f"Schema with id {self.schema_id} not found.")

        return f"{self.schema_name}.{self.name}"
