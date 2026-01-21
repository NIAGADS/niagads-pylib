from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.schema import ForeignKey


class ExternalDatabaseMixin(object):
    """
    Mixin providing fields and a unique constraint for linking to an external database and source identifier.

    Fields:
        external_database_id (int): Foreign key to core.externaldatabase.external_database_id.
        source_id (str): Source identifier within the external database.

    Constraints:
        - Unique constraint on (external_database_id, source_id) to ensure each source_id is unique within its external database.
    """

    external_database_id: Mapped[int] = mapped_column(
        ForeignKey("core.externaldatabase.external_database_id"),
        nullable=False,
        index=True,
    )
    source_id: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "external_database_id", "source_id", name="uq_externaldb_source"
        ),
    )


class OntologyTermMixin(object):
    ontology_term_id: Mapped[int] = mapped_column()
