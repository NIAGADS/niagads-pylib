# ASK NIAGADS prototype

The existing application exposes `POST /ask`. One PydanticAI agent uses fixed API
GET tools. The API query service generates embeddings through OpenRouter using
the ETL default model. No SQL, ORM changes, stored-vector regeneration, or database
retrieval changes are part of this prototype. The UI lives in the other repository at
`apps/open-access-api-client`. Work stays on branches based on `refactor/api`
(Python) and `app/oa-api` (frontend).

## Installation and configuration

For an existing root Poetry development environment, install the optional group:

```bash
poetry install --no-root --with ask
```

The Open Access API project also declares the runtime dependencies in its own
manifest/lock. It follows the base branch's Python 3.12–3.13 requirement and
Polylith brick/package mappings. The prepared cloud interpreter is
`projects/open-access-api/.venv/bin/python`; source checkouts use
`PYTHONPATH=components:bases`. Dependency versions verified for this prototype:
PydanticAI Slim 2.57.0, Logfire 5.2.0, AI SDK 7.0.143, and AI SDK React 4.0.147.
The installed Vercel adapter explicitly supports SDK version 7.

Configure server process variables (secret values belong in secure settings):

| Variable | Purpose/default |
| --- | --- |
| OPENROUTER_API_KEY | Server-side OpenRouter credential; not required for mock tests |
| OPENROUTER_EMBEDDING_TIMEOUT | 20 seconds per provider HTTP request, maximum 30 |
| ASK_MODEL | Explicit tool-capable OpenRouter model ending in `:free`; no default/fallback |
| ASK_MODEL_REQUESTS | 8 per query, maximum 12 |
| ASK_TOOL_CALLS | 12 per query, maximum 20 |
| ASK_API_TIMEOUT | 20 seconds per API tool, maximum 30 |
| ASK_DEADLINE | 90 seconds for the whole query, maximum 120 |
| ASK_TELEMETRY | false; enables optional Logfire instrumentation |
| LOGFIRE_TOKEN | Optional server-side telemetry credential |
| ASK_CAPTURE_CONTENT | false; explicitly opt in to model/prompt/tool content capture |

Never configure paid fallback models. Availability/tool support of a chosen free
model must be verified with a bounded live call on the user's system. Provider
construction is isolated in `ask/provider.py`; future Bedrock work can replace that
construction while keeping tools, result contracts, and the frontend transport.
No Bedrock integration is implemented now.

On a system with the existing API configured and working, run its usual entrypoint:

```bash
PYTHONPATH=components:bases poetry run uvicorn niagads.open_access_api.app:app
```

Existing API startup still requires the database/cache. The cloud will never
connect to that database. Do not supply database credentials to the cloud.

To review real embedding generation without starting the API or accessing a
database, configure `OPENROUTER_API_KEY` securely and run:

```bash
PYTHONPATH=components:bases projects/open-access-api/.venv/bin/python - <<'PY'
import asyncio
from niagads.api.common.services.embeddings import OpenRouterQueryEmbedding

generator = OpenRouterQueryEmbedding()
vector = asyncio.run(generator.generate("Alzheimer disease association studies"))
print({"model": generator.MODEL, "dimensions": len(vector)})
PY
```

This contacts OpenRouter for a real vector and reports the model and dimensions;
it does not print credentials or the vector. A missing model/catalog identity,
rejected key, or network failure produces an explicit error. Chat requires its
separate `ASK_MODEL` selection as described above; embedding generation does not.

## Cloud prototype validation

Run tests only when explicitly requested, as required by repository AGENTS.md.
The focused tests use mock API/model dependencies and need no database, model
key, embedding download, or Logfire credentials:

```bash
PYTHONPATH=components:bases projects/open-access-api/.venv/bin/python -m pytest \
  --confcutdir=test/bases/niagads/open_access_api/ask \
  test/bases/niagads/open_access_api/ask -q
```

For browser checks, this test-only runner imports the **existing application**,
overrides its lifespan and assistant dependencies, and uses synthetic test data:

```bash
PYTHONPATH=components:bases projects/open-access-api/.venv/bin/python \
  test/bases/niagads/open_access_api/ask/serve_prototype.py
```

It binds port 8010. Run the frontend with `ASK_API_URL=http://127.0.0.1:8010`.
Queries containing `dashboard`, `transcript`, or `phenotype` exercise the
corresponding deterministic test scenarios; other queries show synthetic gene
evidence. This fake model does not evaluate real question interpretation. Never
deploy this test harness. It neither starts another production API nor changes
the normal application lifespan.

## What is connected and what is pending

- Tools call existing gene, variant, and track record operations, gene structure,
  and gene/variant associations. They consume the API's list-based `RecordResponse`
  data, bound response bytes/rows, and report retrieval failures. Variant lookups
  accept refSNP, structural, and positional allelic identifiers. Association tools
  retain the existing `page` and `flank` parameters and API page-number limit.
- Gene/track semantic query endpoints now generate query embeddings through
  OpenRouter before invoking their existing retrieval methods. The agent sends
  search text and never receives or generates the vector. Variant semantic search
  remains planned.
- The embedding adapter uses the user-selected ETL default,
  `LiquidAI/LFM2.5-Embedding-350M`. It resolves the provider's model ID by requiring
  exactly one matching `hugging_face_id` in OpenRouter's embedding catalog. A
  missing, ambiguous, or unverifiable model returns an explicit unavailable error;
  it never switches embedding models. No local model is loaded.
- Raw query text is sent to `/api/v1/embeddings` with float encoding. The response
  must contain one finite, nonzero vector from the selected model; it is normalized
  to unit length, matching the inspected ETL generator's default. Missing credentials
  or provider failures stop search before retrieval. Existing API response caching
  continues to avoid embedding calls when a query response is already cached.
- OpenRouter catalog access was blocked by the cloud proxy during implementation.
  Model availability, inference, tokenization/encoding compatibility, and stored
  vector dimensions still require a live check. The adapter's wiring is implemented;
  successful live semantic retrieval is not yet verified.
- `/record/region/associations` accepts `region=chr19:100-200` **or**
  `chr=19&start=100&end=200`, plus existing format/content/page parameters. Its
  declared response models match the gene-association endpoint. Valid input
  returns the existing HTTP 501 not-implemented response; invalid coordinates
  return 422. Its OpenAPI operation carries `x-status: planned`, following the
  base branch's convention. No database context or query is invoked by the placeholder.
- Transcript tools retrieve gene structure, select the exact transcript ID,
  and pass its returned location to the region endpoint. Missing/ambiguous
  transcript selection requests clarification; it does not use the full gene.
- Phenotype-to-gene retrieval explicitly reports unavailable. It does not use
  semantic similarity as evidence of a disease association. Future ORM/API work
  is listed in root TODO.md, including both curated and ±10 kb proximity sources.
- API help uses FastAPI's OpenAPI generation for the registered routes. Its
  operation catalog preserves `x-status` for planned endpoints. Its
  operation catalog does not depend on application-level server metadata, which
  currently prevents the full legacy `/openapi.json` export from validating.
  Existing application metadata and its factory were not changed to repair that
  unrelated refactor issue.

## Response contract and extension points

The official Vercel UI stream carries text/tool events and a final
`data-niagads-result` part with a validated `AskResponse`:

```json
{
  "version": 1,
  "status": "ok",
  "results": [{
    "id": "server-issued-result-id", "kind": "genes", "rows": [],
    "page": 1, "limit": 50, "has_more": false,
    "sources": [], "parameters": {}, "warnings": []
  }],
  "presentation": [{
    "component": "table", "result_id": "server-issued-result-id",
    "title": "Retrieved evidence", "slot": "primary"
  }],
  "warnings": []
}
```

This is a schema example, not a real query result. Results are run-local and
server-owned; tools send bounded previews/result IDs to the model, not full
datasets. A presentation cannot reference a result from another run. The final
text is separate from all displayed data. Missing/invalid components are not
executed. Status distinguishes empty, unsupported, clarification, and retrieval
failures; provider/limit failures use safe stream errors.

Variant records use result kind `variants` and the existing table presentation.
Variant annotations are not phenotype association evidence; source charts require
gene evidence or association rows. At most 50 records from an API page are retained;
larger pages include an explicit truncation warning.

Supported components are `table` and `association_source_bar`. Source bars count
evidence entries in the retrieved page, not all genes or causal importance.
Curated evidence retains its list name, assertion/qualifiers and source; proximity
evidence retains the stable track, variant, and window. Multiple evidence entries
belong to one deduplicated gene. The known-AD-locus flag remains explicit rather
than acquiring an invented curated-list name. The contract supports these fields;
population of phenotype evidence awaits the deferred ORM methods.

To add a component: extend the backend Presentation discriminator, validate its
result kind/options in ResultStore, mirror its runtime schema in frontend
`app/ask/contracts.ts`, and add an adapter to the explicit registry in Results.tsx.
Reuse an existing component contract. Add both backend and frontend tests before
allowing the model to select it. Never accept arbitrary JSX, HTML, CSS, or URLs.

History is browser-memory only and cleared on reload/new session. At most 12
messages/16,000 text characters enter a run; the request body is capped at 64 KiB.
Client-submitted tool results/datasets are discarded, and only user/assistant
text is allowed. Follow-up evidence is re-fetched. There is no Valkey/Cognito
integration or cross-visit persistence in these branches.

## Local handoff checks

1. Supply existing database/cache settings only on the user's system. Confirm
   existing API operations and their authorization boundaries work there.
2. Implement deferred retrieval in the ORM layer under separately approved scope;
   wire the region placeholder and future phenotype API through existing services.
3. Configure `OPENROUTER_API_KEY` server-side. Confirm OpenRouter advertises the
   exact ETL embedding model and returns compatible query vectors. Validate against
   the stored model/version, dimensions, and encoding. Do not switch models or
   regenerate stored embeddings for this feature.
4. Verify real transcript coordinates and both evidence paths, pagination at data
   scale, correct phenotype selection, and provenance. Variant-impact querying
   remains deferred.
5. Select a current free tool-capable model, then run bounded live model/API calls.
   Check tool arguments, grounding, rate-limit behavior, and browser output.
6. If telemetry is enabled, confirm correlation/timing/usage without credentials,
   authorization headers, or large result datasets. Content capture stays off
   unless explicitly enabled. Telemetry availability cannot block query serving.

Cloud mock tests do not establish live database/provider correctness.
