from niagads.genomicsdb.schema.mixins import (
    HousekeepingMixin,
    LookupTableMixin,
    TransactionTableMixin,
)


class DeclarativeTableBase(LookupTableMixin, TransactionTableMixin, HousekeepingMixin):
    __abstract__ = True


class DeclarativeMaterializedViewBase(LookupTableMixin):
    __abstract__ = True
    document_primary_key = None  # so we can do primary key lookups on RAG documents
