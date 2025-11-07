"""`ExternalDB` database model"""

from niagads.genomicsdb.models.reference.base import ReferenceSchemaBase
from pydantic import BaseModel
from sqlalchemy import String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


class ExternalDatabaseRef(BaseModel):
    name: str
    version: str

    @classmethod
    def from_xdbref(cls, xdbref: str):
        """
        Create an ExternalDatabaseRef from a validated 'name|version' string.

        Args:
            xdbref (str): The external database reference string in the format 'name|version'.

        Returns:
            ExternalDatabaseRef: Instance with name and version populated.
        """
        name, version = xdbref.rsplit("|", 1)
        return cls(name=name, version=version)


class ExternalDatabase(ReferenceSchemaBase):
    __tablename__ = "externaldatabase"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_externaldatabase_name_version"),
    )

    external_database_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(300), nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=True)
    download_url: Mapped[str] = mapped_column(String(300), nullable=True)
    download_date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
