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
| OPENROUTER_API_KEY | Server-side OpenRouter credential; required for integration tests |
| OPENROUTER_EMBEDDING_MODEL | Configurable embedding ID; currently restricted to `liquid/lfm-2.5-embedding-350m:free` (default) |
| OPENROUTER_EMBEDDING_TIMEOUT | 20 seconds per provider HTTP request, maximum 30 |
| ASK_MODEL | Chat model ID or OpenRouter router, e.g. `openrouter/free`; no chat-model allowlist |
| ASK_MODEL_REQUESTS | 8 per query, maximum 12 |
| ASK_TOOL_CALLS | 12 per query, maximum 20 |
| ASK_API_TIMEOUT | 20 seconds per API tool, maximum 30 |
| ASK_DEADLINE | 90 seconds for the whole query, maximum 120 |
| ASK_TELEMETRY | false; enables optional Logfire instrumentation |
| LOGFIRE_TOKEN | Optional server-side telemetry credential |
| ASK_CAPTURE_CONTENT | false; explicitly opt in to model/prompt/tool content capture |

OpenRouter can choose the chat model per request when `ASK_MODEL` names a router.
The chat setting has no embedding-model restriction. Tool support of the chosen
chat model/router must be verified with a bounded live call. Provider
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
from niagads.api.common.config import QueryEmbeddingSettings
from niagads.api.common.services.embeddings import OpenRouterQueryEmbedding

settings = QueryEmbeddingSettings.from_env()
generator = OpenRouterQueryEmbedding(settings)
vector = asyncio.run(generator.generate("Alzheimer disease association studies"))
print({"model": settings.OPENROUTER_EMBEDDING_MODEL, "dimensions": len(vector)})
PY
```

This contacts OpenRouter for a real vector and reports the model and dimensions;
it does not print credentials or the vector. A rejected model, key, or network
failure produces an explicit error. Chat requires its
separate `ASK_MODEL` selection as described above; embedding generation does not.

## Integration tests

Run tests only when explicitly requested, as required by repository AGENTS.md.
The ASK tests use the shared API `client` fixture and the application's normal
startup, database, cache, and configured OpenRouter model. Install the optional
`ask` dependency group first. Pytest loads `../.env` relative to the repository
root before collecting tests, preserving existing process environment values.
Source paths are configured in `pyproject.toml`.

```bash
poetry run pytest test/bases/niagads/open_access_api/ask
```

To check collection without starting services or sending inference requests:

```bash
poetry run pytest --collect-only test/bases/niagads/open_access_api/ask
```

The streaming cases submit two live ASK questions: an APOE record table and an
APOE association summary chart. Each question can use up to `ASK_MODEL_REQUESTS`
model requests (8 by default), with provider retries potentially adding HTTP
attempts. The two query endpoint cases can each request an OpenRouter embedding
on a cache miss. Run them only when live service/provider use is intended.
Missing configuration and service failures are reported as failures, not skipped
or replaced with synthetic data. For browser checks, use the normal API
entrypoint and point the frontend's `ASK_API_URL` at that running application.

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
- The embedding adapter sends `OPENROUTER_EMBEDDING_MODEL` directly to OpenRouter.
  The setting defaults to and currently permits only
  `liquid/lfm-2.5-embedding-350m:free`, the user-supplied ID for the ETL model.
  It never routes to another embedding model or loads a local model. Catalog
  discovery is not required. Future model changes require extending the allowed
  embedding IDs alongside compatible stored vectors and invalidating cached
  semantic responses; changing this setting does not regenerate stored embeddings.
- Raw query text is sent to `/api/v1/embeddings` with float encoding. The response
  must contain one finite, nonzero vector from the selected model; it is normalized
  to unit length, matching the inspected ETL generator's default. Missing credentials
  or provider failures stop search before retrieval. Existing API response caching
  continues to avoid embedding calls when a query response is already cached.
- OpenRouter access was blocked by the cloud proxy during implementation.
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
  "version": 2,
  "status": "ok",
  "results": [{
    "id": "server-issued-result-id", "entity": "gene",
    "annotation": "report", "content": "full", "rows": [],
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

Variant reports use `entity: "variant"`, `annotation: "report"`, and the existing
table presentation.
Association source charts require `annotation: "associations"` and
`content: "summary"`. Association tools accept the existing API content selector:
use `full` for individual `VariantAssociation` records or `summary` for existing
`DynamicRecord` rows containing `track`, `traits`, and `num_associations`.
The operation registry describes both responses with the existing record models.

Supported components are `table` and `association_source_bar`. Source bars display
the API's `num_associations` values for the tracks in the returned summary.
ASK does not recount individual associations, aggregate gene annotation evidence,
or infer scientific evidence from these counts. A summary page can contain only
some tracks; preserve pagination and truncation warnings. At most 50 returned
records are retained under the current adapter limit. Gene reports and full
association records can be displayed in tables, not this chart.

Entity identity uses `niagads.common.types.Entity`; annotation kinds use
`niagads.api.common.types.AnnotationKind`. A report is an annotation kind; records
remain the API's representation of retrieved information. Search candidates have
`annotation: null` because a match is not a full entity report. Version 2 replaces
the former mixed `kind` field; backend and frontend must be updated together.

Supported retrieval operations are declared in `ask/operations.py`, with an
endpoint, entity, annotation kind, and the existing `ResponseConfiguration`
response/record model pair (for example, `RecordResponse` and `Gene`). This
metadata describes the requested JSON content, including association summaries; it does not
introduce a second record-model implementation or change route validation.
Association summary entries use `content=ResponseContent.SUMMARY` and
`record_model=DynamicRecord`. ASK results include `content` so presentation
validation can distinguish summaries from full records. Model previews retain
`num_associations` alongside the track identifier.
Search operations are derived from entries using `SearchMatch`, independently
of their operation names. Registering an entity does not enable new retrieval.

After changing the enums or `SOURCE_CHART_TYPES`, regenerate and commit the
frontend constants from this repository (no API startup or provider call):

```bash
PYTHONPATH=components:bases python -m niagads.open_access_api.ask.export_types \
  ../niagads-viz-monorepo/apps/open-access-api-client/app/ask/types.generated.ts
```

The frontend imports the generated enums and chart compatibility rules for its
runtime validation. New annotations can reuse the table without new renderers;
charts require explicit compatible entity/annotation pairs.

To add a component: extend the backend Presentation discriminator, validate its
entity/annotation compatibility in ResultStore, mirror its runtime schema in
frontend `app/ask/contracts.ts`, and add an adapter to the explicit registry in
Results.tsx. Reuse an existing component contract. Add both backend and frontend tests before
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
3. Configure `OPENROUTER_API_KEY` and `OPENROUTER_EMBEDDING_MODEL` server-side.
   Confirm OpenRouter returns compatible query vectors for the selected ID. Validate against
   the stored model/version, dimensions, and encoding. Do not switch models or
   regenerate stored embeddings for this feature.
4. Verify real transcript coordinates and both evidence paths, pagination at data
   scale, correct phenotype selection, and provenance. Variant-impact querying
   remains deferred.
5. Configure a tool-capable chat model or router, then run bounded live model/API calls.
   Check tool arguments, grounding, rate-limit behavior, and browser output.
6. If telemetry is enabled, confirm correlation/timing/usage without credentials,
   authorization headers, or large result datasets. Content capture stays off
   unless explicitly enabled. Telemetry availability cannot block query serving.

Cloud mock tests do not establish live database/provider correctness.
