# RAG Document Citation & Evidence Graph - Deep Dive

## Core Concept

Create a knowledge graph that connects your vector-indexed RAG document chunks with structured genomics entities and evidence relationships, enabling multi-hop reasoning and explainable AI responses.

## Graph Schema Design

### Vertices

1. **`rag_chunk`** - Individual document segments (vector-indexed)
   - `chunk_id` (primary key)
   - `document_id` (references source document)
   - `content` (the text chunk)
   - `embedding_vector` (for similarity search)
   - `chunk_position` (order within document)
  
  > if a rag_chunk == entity record, chunk_position is not necessary, chunk_position is for splitting of source documents (e.g., journal articles)

1. **`document`** - Source publications/reports
   - `document_id` (primary key)
   - `title`, `authors`, `publication_date`
   - `pmid`, `doi` (external identifiers)
   - `document_type` (paper, clinical_report, database_entry)

2. **`claim`** - Extracted assertions/statements
   - `claim_id` (primary key)
   - `claim_text` (the assertion)
   - `confidence_score` (extraction confidence)
   - `claim_type` (causal, associative, descriptive)

3. **`evidence`** - Supporting or refuting data points
   - `evidence_id` (primary key)
   - `evidence_type` (experimental, statistical, observational)
   - `strength` (strong, moderate, weak)

4. **`entity`** - Genomic entities (genes, variants, diseases, etc.)
   - Link to your existing relational tables via IDs
   - Keep this lightweight (just IDs + labels for graph traversal)

### Edges

1. **`chunk` → `contains` → `claim`**
   - A chunk asserts a specific claim
   - Properties: `extraction_method`, `confidence`

2. **`claim` → `supported_by` → `evidence`**
   - Evidence supports a claim
   - Properties: `support_strength`, `evidence_source`

3. **`claim` → `contradicts` → `claim`**
   - Claims that conflict
   - Properties: `conflict_type`, `resolution_status`

4. **`chunk` → `cites` → `document`**
   - Cross-references between documents
   - Properties: `citation_context`

5. **`chunk` → `mentions` → `entity`**
   - Chunk discusses a gene/variant/disease
   - Properties: `mention_count`, `context_type` (primary_subject, background, comparison)

6. **`claim` → `involves` → `entity`**
   - Claim is about specific genomic entities
   - Properties: `role` (subject, object, modifier)

7. **`document` → `studies` → `entity`**
   - Document's primary research focus
   - Properties: `study_type`, `sample_size`

## Use Cases & Query Patterns

### 1. Multi-Source Evidence Aggregation

**Cypher query:**

```cypher
MATCH (e:entity {gene_symbol: 'APOE'})-[:mentioned_in]-(chunk:rag_chunk)-[:contains]->(claim:claim)
      -[:supported_by]->(evidence:evidence)
WHERE evidence.strength IN ['strong', 'moderate']
RETURN claim.claim_text, 
       COUNT(DISTINCT chunk) as supporting_chunks,
       COLLECT(DISTINCT chunk.document_id) as sources
GROUP BY claim
```

**Purpose:** Find all strongly-supported claims about APOE across multiple documents.

### 2. Contradiction Detection

**Cypher query:**

```cypher
MATCH (c1:claim)-[:involves]->(e:entity {entity_id: 'rs7412'})
MATCH (c2:claim)-[:involves]->(e)
MATCH (c1)-[:contradicts]->(c2)
MATCH (c1)<-[:contains]-(chunk1:rag_chunk)-[:cites]->(doc1:document)
MATCH (c2)<-[:contains]-(chunk2:rag_chunk)-[:cites]->(doc2:document)
RETURN c1.claim_text, c2.claim_text, 
       doc1.title, doc1.publication_date,
       doc2.title, doc2.publication_date
ORDER BY doc1.publication_date DESC
```

**Purpose:** Identify conflicting claims about variant rs7412 and trace them to source papers (useful for understanding evolving research).

### 3. Evidence Chain Discovery

**Cypher query:**

```cypher
MATCH path = (gene:entity {gene_symbol: 'APP'})-[:mentioned_in*1..3]-(chunk:rag_chunk)
             -[:contains]->(claim:claim)-[:involves]->(disease:entity {entity_type: 'disease'})
WHERE disease.name CONTAINS 'Alzheimer'
RETURN path, LENGTH(path) as hop_count
ORDER BY hop_count
LIMIT 10
```

**Purpose:** Find indirect evidence chains linking APP gene to Alzheimer's disease through intermediate claims.

### 4. RAG Response Grounding

When your RAG system retrieves chunks via vector similarity:

```cypher
// After vector search returns chunk_ids: [123, 456, 789]
MATCH (chunk:rag_chunk)
WHERE chunk.chunk_id IN [123, 456, 789]
MATCH (chunk)-[:contains]->(claim:claim)-[:supported_by]->(evidence:evidence)
MATCH (chunk)-[:mentions]->(entity:entity)
RETURN chunk.content,
       COLLECT(DISTINCT claim.claim_text) as extracted_claims,
       COLLECT(DISTINCT evidence.evidence_type) as evidence_types,
       COLLECT(DISTINCT entity.gene_symbol) as mentioned_genes
```

**Purpose:** Enrich RAG responses with structured claims and entities, enabling explainable answers.

### 5. Citation Network Analysis

**Cypher query:**

```cypher
MATCH (doc:document)-[:studies]->(gene:entity {gene_symbol: 'BRCA1'})
MATCH (doc)<-[:cites]-(citing_chunk:rag_chunk)-[:part_of]->(citing_doc:document)
RETURN doc.title as seminal_paper,
       doc.publication_date,
       COUNT(DISTINCT citing_doc) as citation_count,
       COLLECT(DISTINCT citing_doc.pmid) as citing_pmids
ORDER BY citation_count DESC
LIMIT 10
```

**Purpose:** Find most-cited papers about BRCA1 in your corpus.

## Integration with Vector Search

### Hybrid Retrieval Pattern

1. **Vector search** (PostgreSQL pgvector or similar):

   ```sql
   SELECT chunk_id, content, embedding_vector <=> query_vector AS similarity
   FROM rag_chunk
   ORDER BY similarity
   LIMIT 20;
   ```

2. **Graph enrichment** (follow up with Cypher):
   - Take returned `chunk_ids`
   - Query graph for connected claims, evidence, entities
   - Rank by evidence strength and citation count

3. **Re-ranking**:
   - Combine vector similarity score with graph-derived metrics:
     - Number of supporting evidence nodes
     - Citation count of source document
     - Entity relevance (how many query entities are mentioned)

## Implementation Strategy

### Phase 1: Extract & Load

- Use NLP pipeline (spaCy, BioBERT) to extract entities and claims from documents
- Store chunks with vector embeddings
- Create graph edges for mentions, citations

### Phase 2: Evidence Linking

- Manual or semi-automated claim extraction
- Link claims to evidence from structured databases (ClinVar, GWAS catalogs)
- Build `supported_by` edges

### Phase 3: Contradiction Detection

- Run similarity analysis on claims mentioning same entities
- Use LLM or rules to identify contradictions
- Create `contradicts` edges

### Phase 4: Query Interface

- Build Python functions (using your PL/Python suggestion) that:
  - Accept RAG query
  - Run vector search
  - Enrich with graph traversal
  - Return structured results with provenance

## Performance Considerations

**What makes this efficient:**

- Vector search is O(log n) with proper indexing (HNSW)
- Graph traversals are O(degree) for local neighborhood queries
- Only store lightweight entities (IDs + names), not full variant/gene records

**What to avoid:**

- Don't create vertices for every variant mention (too many nodes)
- Don't traverse more than 3-4 hops (exponential explosion)
- Cache common subgraph queries (e.g., "top genes for disease X")

## Example: Full Workflow

**User query:** "What evidence links APOE ε4 allele to Alzheimer's risk?"

1. Vector search finds relevant chunks
2. Graph query:

```cypher
MATCH (gene:entity {gene_symbol: 'APOE'})-[:mentioned_in]-(chunk:rag_chunk)
      -[:contains]->(claim:claim)-[:involves]->(variant:entity {variant_id: 'rs429358'})
MATCH (claim)-[:supported_by]->(evidence:evidence)
MATCH (claim)-[:involves]->(disease:entity {name: 'Alzheimers Disease'})
MATCH (chunk)-[:part_of]->(doc:document)
RETURN claim.claim_text,
       evidence.evidence_type,
       evidence.strength,
       doc.title,
       doc.pmid
ORDER BY evidence.strength DESC, doc.publication_date DESC
```

1. Response includes:
   - Extracted claims
   - Evidence strength
   - Source papers with PMIDs (for user verification)
   - Confidence scores

This creates an **explainable RAG system** where every answer can be traced back through the evidence graph to source documents.

## Another suggestion to consider

Variant-Gene-Phenotype Associations

- Vertices: variants (if small curated sets), genes, phenotypes, diseases
- Edges: associated_with, located_in, causes, increases_risk
- Why: Graph queries can discover indirect associations (e.g., "variants in gene X linked to phenotype Y, and other phenotypes connected to Y").
