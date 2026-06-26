# Variant VEP Annotation Summarization Plan

## Summary

Build a two-stage system: first preprocess each VEP JSON record into a compact, deduplicated "variant interpretation packet"; then use an LLM to produce short, factual, embeddable text for semantic search. The LLM should explain what the annotations imply, but it should not infer pathogenicity beyond the evidence present.

The target output is not a clinical interpretation. It is retrieval text: dense, human-readable, scientifically grounded, and useful for queries like "rare upstream variant near gene X with high CADD" or "regulatory variant affecting predicted expression".

This work is motivated by the need to make per-variant VEP and VEP-plugin annotations searchable through a knowledgebase web interface using vector-based semantic similarity. Raw VEP JSON is too redundant, technical, and unevenly structured for direct embedding. A prompt-driven summary can translate compact annotation facts into prose that captures biological context, computational predictions, caveats, and search vocabulary.

## Prompt-Driven Summary Shape

Use one concise paragraph plus optional tagged facts:

```text
This GRCh38 insertion/deletion at chrN:start-end has the most severe VEP consequence upstream_gene_variant. It is located near GENE1 and GENE2, affecting transcript annotations primarily as upstream or downstream variants. The variant has CADD PHRED score X, suggesting it is among the higher/lower ranked substitutions or indels by predicted deleteriousness, but this score alone is not clinical evidence. Enformer predicts altered regulatory activity for [tissue/track summary if available], suggesting possible noncoding regulatory relevance. Known colocated variant IDs and population frequencies indicate [common/rare/not available].
```

Recommended embedding fields:

```json
{
  "variant_id": "...",
  "summary_text": "...",
  "search_terms": [
    "upstream gene variant",
    "CADD PHRED 23.4",
    "GENE",
    "regulatory effect",
    "noncoding variant"
  ],
  "evidence_notes": [
    "VEP consequence: upstream_gene_variant",
    "CADD plugin score present",
    "Enformer plugin score present"
  ],
  "limitations": [
    "No clinical pathogenicity assertion made"
  ]
}
```

## Prompt Templates

Use a structured system prompt:

```text
You summarize genomic variant annotations for semantic search. Use only the supplied annotation packet and supplied glossary. Do not invent disease associations, pathogenicity, gene function, or clinical significance. Explain annotation implications in careful plain language. Prefer "may", "suggests", or "is consistent with" for predictive annotations. Output compact text suitable for vector embedding.
```

Use this user prompt:

```text
Given this preprocessed VEP annotation packet and glossary, write:
1. one 80-140 word human-readable summary;
2. 8-20 search terms;
3. 2-5 evidence notes;
4. 1-3 limitations.

Prioritize: consequence severity, affected gene/transcript context, coding/regulatory/intergenic context, CADD, Enformer, LoF-related fields, colocated variant/frequency context, and allele-specific caveats.

Annotation packet:
{{packet_json}}

Glossary:
{{retrieved_glossary_snippets}}
```

For high-throughput ETL, require JSON output with schema-constrained decoding when the serving stack supports it.

## Knowledge To Incorporate

Use a small retrieval glossary instead of putting all docs in every prompt.

Core glossary sources:

- Ensembl VEP consequence terms, severity order, and IMPACT meanings. Ensembl notes that consequence terms are Sequence Ontology terms, each allele/transcript can differ, and the listed severity ordering is subjective: https://www.ensembl.org/info/genome/variation/prediction/predicted_data.html
- Ensembl VEP data/output format documentation, especially JSON and `Extra` annotations: https://www.ensembl.org/info/docs/tools/vep/vep_formats.html
- CADD documentation for raw vs PHRED-scaled scores and safe language around predicted deleteriousness: https://cadd.gs.washington.edu/info
- VEP plugin documentation/source for plugin-specific fields such as Enformer: https://github.com/Ensembl/VEP_plugins/blob/release/115/Enformer.pm

Also add local project knowledge:

- A field dictionary for the exact VEP/plugin fields emitted by your pipeline.
- A consequence severity map copied from the VEP version used in the ETL.
- A normalization policy for duplicated transcript-level plugin annotations, since the examples show large repeated arrays.

## Recommended Solution

Preprocess first, then summarize.

Preprocessor behavior:

- Collapse duplicate CADD, Enformer, LoF, frequency, and colocated-variant values across transcript consequences.
- Select representative transcript consequences by severity, canonical/MANE/APPRIS status, protein-coding status, and gene symbol.
- Preserve counts, ranges, extrema, and representative examples instead of raw repeated records.
- Keep allele-specific fields explicit, especially `variant_allele`, `allele_string`, and colocated allele frequencies.
- Emit a compact packet small enough for a local model context window.

Model/runtime recommendation:

- For prototyping quality, use OpenRouter or another hosted API to compare 2-3 strong instruction models quickly.
- For local production, use `llama.cpp` or Ollama with a strong open-weight instruction model such as Qwen3 32B-class or larger if latency allows. `llama.cpp` supports CPU/GPU quantized inference, OpenAI-compatible endpoints, continuous batching, and schema-constrained JSON: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- Avoid making Hugging Face TGI the default new deployment choice unless you already depend on it; Hugging Face currently describes TGI as maintenance-mode and points users toward engines such as vLLM, SGLang, and llama.cpp: https://huggingface.co/docs/text-generation-inference/index
- On the 100-core / 512 GB server, cap local inference to about 80-85 CPU threads and under ~435 GB RAM. Start with quantized 30B-40B models for throughput; test 70B-class only if summary quality clearly improves enough to justify slower ETL.

## Test Plan

Evaluate on the provided example files:

- `intergenic.json`: should produce noncoding/intergenic language without overclaiming.
- `regulatory_feature.json` and `motif.json`: should emphasize regulatory context and avoid coding-effect claims.
- `lof.json`: should surface LoF-related annotations only when present and not conflate nearby upstream variants with loss of function.
- `transcript_indel.json`: should prove preprocessing handles many redundant transcript and colocated-variant records.

Acceptance criteria:

- Output contains no unsupported disease, pathogenicity, or treatment claims.
- Consequence, gene, transcript, CADD, Enformer, frequency, and colocated-variant facts match the packet.
- Text is compact enough for embedding and semantically useful without raw JSON.
- Re-running the same packet with temperature 0-0.2 gives stable summaries.

## Assumptions

- The first implementation is a design/prototype, not yet wired into the ETL plugin.
- The summary is for knowledgebase search and triage, not clinical reporting.
- Preprocessing will be deterministic; the LLM will only verbalize and lightly interpret supplied fields.
- The examples are not comprehensive, so the field dictionary and glossary should be extensible as new VEP/plugin annotations appear.
