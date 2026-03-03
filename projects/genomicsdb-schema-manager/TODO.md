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

Complete List of Mixins with __table_args__ and Models Needing Fixes
Database-level Mixins (in mixins)
GenomicRegionMixin (ranges.py)

Defines: enum_constraint("chromosome", HumanGenome), GIST indexes on genomic_region and bin_index
Models inheriting WITH __table_args__ override (LOSING mixin's constraints):
GeneModel (gene/structure.py) ✗
TranscriptModel (gene/structure.py) ✗
ExonModel (gene/structure.py) ✗
TrackInterval (dataset/track.py) ✗
Models inheriting WITHOUT override (OK - inherit mixin's):
Gene (gene/documents.py) - MV, skip in migrations
IntervalBin (reference/interval_bin.py) - OK
EmbeddingMixin (embeddings.py)

Defines: HNSW index on embedding column
Models inheriting WITH __table_args__ override (LOSING mixin's index):
Track (dataset/track.py) ✗
Pathway (reference/pathway.py) ✓ No override
Models inheriting WITHOUT override (OK):
Pathway (reference/pathway.py) - OK
Schema-level Mixins (in schema)
ExternalDatabaseMixin (reference/mixins.py)

Defines: UniqueConstraint("external_database_id", "source_id")
Models inheriting:
GeneTableBase (gene/base.py) - Base class, passes constraint down
Track (dataset/track.py) - Has own __table_args__, overrides ✗
Pathway (reference/pathway.py) - No __table_args__, OK
Various other tables in gene schema (inherit from GeneTableBase)
TableRefMixin (admin/mixins.py)

Defines: NO __table_args__ (just columns and methods)
Models inheriting:
AnnotationEvidence (gene/annotation.py) - Has own __table_args__, OK
ChunkMetadata (ragdoc/documents.py) - Has own __table_args__, OK
