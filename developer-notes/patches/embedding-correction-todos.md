# Embedding correction TODOs

- [ ] update legacy plugins to use document chunking in `EmbeddingGeneratorContextMixin`
- [ ] write plugin to regenerate all embeddings
- [ ] before next regeneration change embedding field in DB to plain `Vector` and create dimension-specific indexes for models
- [ ] re-embed all of variant table with json documents and new model
