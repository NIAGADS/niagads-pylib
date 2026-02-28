from niagads.genomicsdb.schema.admin.base import AdminTableBase
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship


class AdminSchemaCatalog(AdminTableBase):
    """
    Catalog of database schemas.
    """

    __tablename__ = "schemacatalog"

    schema_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )

    tables: Mapped[list["AdminTableCatalog"]] = relationship(
        "AdminTableCatalog", back_populates="schema", cascade="all, delete-orphan"
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
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    schema: Mapped[AdminSchemaCatalog] = relationship(
        "AdminSchemaCatalog", back_populates="tables"
    )
