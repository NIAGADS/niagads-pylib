from niagads.database.helpers import enum_column, enum_constraint
from niagads.database.types import RAGDocType
from sqlalchemy import TEXT, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column


class ChunkMetadataMixin:
    """
    mixin for chunk boundaries and metadata for structured and unstructured documents.
    """

    __abstract__ = True

    __tablename__ = "chunkmetadata"
    __table_args__ = enum_constraint("document_type", RAGDocType)

    chunk_metadata_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    document_section: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default="FULL", default="FULL"
    )
    document_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=True)
    chunk_hash: Mapped[bytes] = mapped_column(LargeBinary(32), nullable=False)
    chunk_text: Mapped[str] = mapped_column(TEXT, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=True)
    chunk_id: Mapped[str] = mapped_column(
        String(128), nullable=False, unique=False, index=True
    )
