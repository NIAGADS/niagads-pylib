from niagads.genomicsdb.schema.mixins import HousekeepingMixin, LookupTableMixin


class DeclarativeTableBase(LookupTableMixin, HousekeepingMixin):
    __abstract__ = True


class DeclarativeMaterializedViewBase(LookupTableMixin):
    document_primary_key = None  # so we can do primary key lookups on RAG documents
    __abstract__ = True
