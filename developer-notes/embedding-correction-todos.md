# Embedding correction TODOs

## Truncation issue

`TextEmbeddingGenerator.generate()` passes text directly to
`SentenceTransformer.encode()`. The current default, `all-MiniLM-L6-v2`,
truncates inputs beyond its 256-token limit. The loaders do not currently
measure token lengths or split oversized inputs. Batch embedding does not
split individual inputs.

The stored text and its hash describe the full input, even when the vector
represents only its beginning. Successful encoding and matching hashes do
not establish that all content was embedded.

Evidence from this review:

- Track `NG00161_A3BA69CE_STD_OA`: 532 tokens after the loader's Pydantic
  serialization and embedding exclusions. MiniLM retains 256 tokens and
  omits 276, including all experimental-design covariates and participant
  phenotypes. This was evaluated from the metadata file, not a persisted
  embedding or historical run configuration.
- Synthetic ontology term: 284 tokens; the final two synonyms and namespace
  fall beyond the limit. This demonstrates the mechanism, not the frequency
  among actual ontology terms.
- Variant annotations: consequence, allele-frequency, and predictor phrases
  are combined into one input without length checking. Actual affected
  variant counts have not been measured.

## Plan: switch the default to BGE-M3

Goal: Use its 8,192-token input window to preserve more related annotation
and metadata content together. It is retrieval-oriented, but improved
genomics retrieval remains to be established by evaluation.

- [ ] Owl parser must be updated to generate json instead of text
- [ ] Evaluate `BAAI/bge-m3` against representative genomics queries and
  expected relevant records before migration.
- [X] Add BGE-M3 to the existing model registry and make it the default for
  migrated RAG document loaders and their query encoder.
- [ ] Keep token-length checks: BGE-M3 can still truncate inputs exceeding
  its limit. Full gene documents containing all transcripts and exons can
  exceed that window.
- [ ] Evaluate encoding throughput and memory with the actual document
  lengths and batch sizes. BGE-M3 requires more resources than MiniLM.

Model specifications: [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
and [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3).

## Schema and query changes

- [x] Migrate `ragdoc.chunkembedding.embedding` from `vector(384)` to
  `vector(1024)` and update its ORM mapping.
- [x] Rebuild the corresponding HNSW cosine index for the new vectors.
- [ ] Generate new vectors from source text; existing vectors cannot be
  padded or resized into valid BGE-M3 embeddings. Stage the replacement
  vectors before the database/query cutover.
- [ ] Update query encoding to BGE-M3 at cutover. Restrict similarity searches
  to the matching embedding model; different models do not share a vector
  space, even when their dimensions match.
- [ ] Account for the shared `EmbeddingMixin`: both `ChunkEmbedding` and
  `Variant` currently inherit its `Vector(384)` mapping. Keep the variant
  mapping and loader's model explicitly at 384/MiniLM until the later variant
  migration. Do not change the shared default in a way that breaks that path.

## One-off patch for existing RAG documents

- [ ] Re-embed existing documents from `ragdoc.chunkmetadata.chunk_text`,
  using existing batch embedding and database-loading infrastructure.
- [ ] Audit token lengths using the BGE-M3 tokenizer. Inputs within its limit
  can be re-embedded intact; larger inputs require chunking first.
- [ ] Identify rows without stored text and report them for source recovery;
  do not fabricate replacement text.
- [ ] Preserve metadata links and content hashes when text is unchanged;
  record the new embedding model, embedding date, and patch ETL run.
- [ ] Make the patch resumable and avoid recalculating completed BGE-M3
  chunk/model/hash combinations.

## Later work

- [ ] Patch variant embeddings separately: audit stored
  `functional_annotation_summary.embedded_text`, migrate their vector column
  and index, and regenerate embeddings. Handle oversized inputs explicitly.
- [ ] Update ontology, track, gene, and variant plugins to measure final
  embedding input lengths, including any context or special tokens, and
  split oversized inputs into meaningful chunks.
- [ ] Use `document_embeddings.py` as the eventual example once its chunking
  implementation is completed and reviewed; its current section assembly
  does not resolve truncation.
- [ ] Retain full chunk text and provenance so future model changes can be
  applied without rebuilding source documents.
