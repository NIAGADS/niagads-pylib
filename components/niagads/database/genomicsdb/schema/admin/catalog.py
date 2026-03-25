from niagads.database.genomicsdb.schema.admin.base import AdminTableBase
from pydantic import BaseModel, ConfigDict
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, literal, select
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.ext.asyncio import AsyncSession

class TableRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    table: str
    schema: str
    table_id: int
    schema_id: int
    table_primary_key: str

class SchemaCatalog(AdminTableBase):
    """
    Catalog of database schemas.
    """

    __tablename__ = "schemacatalog"
    __table_args__ = AdminTableBase.__table_args__

    schema_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )


class TableCatalog(AdminTableBase):
    """
    Catalog of tables within a schema.
    """

    __allow_unmapped__ = True
    __tablename__ = "tablecatalog"
    __table_args__ = (
        UniqueConstraint("schema_id", "name", name="uq_schema_table_name"),
        AdminTableBase.__table_args__,
    )

    table_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    schema_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("admin.schemacatalog.schema_id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    table_primary_key: Mapped[str] = mapped_column(
        String(50), nullable=False, index=False
    )

    _schema: str

    async def full_name(self, session: AsyncSession = None) -> str:
        """
        Returns the 'schema.table' name representation for this table.
        If the schema relationship is not loaded, fetches it from the session.

        Args:
            session: SQLAlchemy Session or AsyncSession (required if schema is not loaded)

        Returns:
            str: schema.table name
        """
        if self._schema is None:
            if session is None:
                raise ValueError("Session required to fetch schema if not loaded.")

            result = await session.execute(
                select(SchemaCatalog.name).where(
                    SchemaCatalog.schema_id == self.schema_id
                )
            )
            self._schema = result.scalar_one_or_none()
            if self._schema is None:
                raise ValueError(f"Schema with id {self.schema_id} not found.")

        return f"{self._schema}.{self.name}"
    
    async def get_table_ref(self, session: AsyncSession, table_class) -> TableRef:
        schema_name, table_name = table_class.table_name(session).split(".")
    
        result = (await session.execute(
            select(
                SchemaCatalog.name,
                TableCatalog.name,
                TableCatalog.table_id,
                TableCatalog.table_primary_key,
                SchemaCatalog.schema_id
            )
            .join(SchemaCatalog, TableCatalog.schema_id == SchemaCatalog.schema_id)
            .where(
                SchemaCatalog.name == schema_name,
                TableCatalog.name == table_name,
            )
        )).first()
        
        if result is None:
            raise ValueError(f"Table '{schema_name}.{table_name}' not found in DB catalog.")

        return TableRef(**result)

