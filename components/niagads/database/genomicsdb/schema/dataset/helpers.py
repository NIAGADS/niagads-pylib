"""
Helpers and utility functions for track schema models.

This module should contain non-ORM-specific helpers, constants, or data transformation utilities
used by schema models
"""

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column


def track_fk_column(nullable: bool = False, index: bool = True) -> Mapped[int]:
    """
    Create a mapped_column for a track_id foreign key.

    Args:
        nullable (bool): Whether the column is nullable. Defaults to False.
        index (bool): Whether to add an index. Defaults to True.

    Returns:
        Mapped[int]: SQLAlchemy mapped_column for track_id foreign key to
            dataset.track.track_id.

    Example:
        track_id: Mapped[int] = track_fk_column()
    """
    return mapped_column(
        Integer, ForeignKey("dataset.track.track_id"), nullable=nullable, index=index
    )
