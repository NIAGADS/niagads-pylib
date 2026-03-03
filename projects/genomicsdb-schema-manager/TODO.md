# TODOs

- for functions, views, triggers, etc use [alembic_utils](https://github.com/olirice/alembic_utils) (already added as depedency)

unpack all mixin table args

```
class GeneModel(GeneTableBase, GenomicRegionMixin, IdAliasMixin):
    __tablename__ = "gene"
    __table_args__ = (
        *GenomicRegionMixin.__table_args__,  # Unpack mixin's args first
        CheckConstraint(...),                 # Then add subclass's args
    )
```
