"""`Pathway` database model"""

from typing import Optional
from niagads.database.mixins import EmbeddingMixin

from niagads.genomicsdb.schema.mixins import IdAliasMixin
from niagads.genomicsdb.schema.reference.base import ReferenceTableBase
from niagads.genomicsdb.schema.reference.mixins import ExternalDatabaseMixin
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Pathway(ReferenceTableBase, ExternalDatabaseMixin, IdAliasMixin, EmbeddingMixin):

    __tablename__ = "pathway"
    _stable_id = "source_id"  # from the ExternalDBMixin

    __table_args__ = (
        *EmbeddingMixin.get_indexes(ReferenceTableBase.metadata.schema, "pathway"),
        *ExternalDatabaseMixin.__table_args__,
    )
    pathway_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
