"""
Helpers and utility functions for gene schema models.

This module should contain non-ORM-specific helpers, constants, or data transformation utilities
used by schema models
"""

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column


def gene_fk_column(nullable: bool = False, index: bool = True) -> Mapped[int]:
    """
    Create a mapped_column for a gene_id foreign key.

    Args:
        nullable (bool): Whether the column is nullable. Defaults to False.
        index (bool): Whether to add an index. Defaults to True.

    Returns:
        Mapped[int]: SQLAlchemy mapped_column for gene_id foreign key to
            gene.gene_id.

    Example:
        gene_id: Mapped[int] = gene_fk_column()
    """
    return mapped_column(
        Integer, ForeignKey("gene.gene.gene_id"), nullable=nullable, index=index
    )
