"""
Base class for the `Gene` schema models in the genomicsdb database.
Uses DeclarativeModelBaseFactory to create a SQLAlchemy DeclarativeBase with housekeeping fields.
"""

from niagads.genomicsdb.schema.base import (
    DeclarativeTableBase,
    DeclarativeMaterializedViewBase,
)


from sqlalchemy import ForeignKey, MetaData
from sqlalchemy.orm import Mapped, mapped_column


class GeneSchemaBase:
    metadata = MetaData(schema="gene")
    stable_id = "ensembl_id"


class GeneTableBase(DeclarativeTableBase, GeneSchemaBase): ...


class GeneMaterializedViewBase(DeclarativeMaterializedViewBase, GeneSchemaBase): ...


def gene_id_column() -> Mapped[int]:
    """
    Returns a mapped_column for an external_database_id foreign key.

    The column references core.externaldatabase.external_database_id, is not nullable,
    and is indexed for efficient lookups.

    Returns:
        Mapped[int]: SQLAlchemy mapped_column for external_database_id foreign key.
    """
    return mapped_column(
        ForeignKey("gene.externaldatabase.external_database_id"),
        nullable=False,
        index=True,
    )
