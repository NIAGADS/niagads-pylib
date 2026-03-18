"""
Helpers and utility functions for gene schema models.

This module should contain non-ORM-specific helpers, constants, or data transformation utilities
used by schema models
"""

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column


def ontology_term_fk_column(nullable: bool = False, index: bool = True) -> Mapped[int]:
    """
    Create a mapped_column for a ontology_term_id foreign key.

    Args:
        nullable (bool): Whether the column is nullable. Defaults to False.
        index (bool): Whether to add an index. Defaults to True.

    Returns:
        Mapped[int]: SQLAlchemy mapped_column for ontology_term_id foreign key to
            reference.ontology.ontology_term_id.

    Example:
        ontology_term_id: Mapped[int] = ontology_term_id_fk_column()
    """
    return mapped_column(
        Integer,
        ForeignKey("reference.ontologyterm.ontology_term_id"),
        nullable=nullable,
        index=index,
    )
