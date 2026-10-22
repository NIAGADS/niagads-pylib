# ASK NIAGADS prototype

## Brief chat responses and dashboard results

ASK instructions require brief summaries instead of Markdown tables, long record
lists or API catalogs. The frontend supplies dashboard/download links; the model
must not invent them or claim presentation succeeded. Follow-ups re-fetch needed
evidence; browser-held records stay outside trusted model history.

Gene/variant/track tools use existing GeneBrief, VariantBrief and TrackMetadataBrief
configurations with content=summary. The UI renders single reports as summary
Cards and provides a fixed full-record API link. Lists/charts live on a temporary
conversation dashboard. Protocol v4 is unchanged. See the current handoff and
developer-notes/plans/ask/chat-dashboard-navigation.md. No synthetic tests were
added; live model behavior remains unvalidated.

## Structured query interpretation

ASK uses one PydanticAI retrieval agent. Clear requests retrieve directly. When
concept decomposition or scope materially benefits, it can call record_query_plan
with a fixed, bounded QueryPlan schema, before or after resolving identifiers.
There is no mandatory interpretation call before retrieval. Optional planning
records a short goal, intent, flat concepts/constraints and necessary scope or
evidence hints, not an exhaustive workflow. It is not retrieved evidence.

Each native tool return determines the next action. Gene/structure tools select
per-call evidence_fields so dependencies discovered during execution are supported.
Structure summaries expose transcript IDs/spans; exons remain opt-in. Full records
stay in ResultStore. Available gene-annotation requests cover both full gene
annotation and gene associations. Returned source track IDs identify associated
datasets; get_track supplies their metadata when needed. Semantic candidates do
not establish an association. Empty associations do not erase gene evidence.

The native loop retains request/tool/token/deadline budgets, retry handling and
max_tokens=2000. The optional planning call uses the same tool argument validation
as retrieval: invalid inputs get the existing bounded native retry, then an honest
error if exhausted. No fabricated default interpretation, JSON repair or silent
fallback occurs. Already retrieved results remain available on failure.

`data-niagads-plan` is emitted only for a successfully recorded interpretation,
including in feedback; clear requests need no plan event. The frontend mirrors its strict schema; deploy both repos together.
Browser-supplied plan/tool parts are discarded. Each turn interprets sanitized
text and re-fetches evidence when needed; browser dashboards are not model memory.

Only materially ambiguous dependent actions need clarification. Available tools
should resolve inputs first; independent work can proceed. `clarify_request`
records the existing clarification outcome and preserves retrieved results. The
agent then asks a brief question rather than silently choosing a transcript or
inventing scope. Unsupported retrieval must be reported without substituting
metadata for genomic data. The location-aware `get_track_data` agent tool remains
an honest placeholder with no HTTP call; it is distinct from the dashboard's
manual parameter-free `/record/track/{track_id}/data` fetch.

Direct `/query/*` primitives, embeddings and retrieval behavior are unchanged.
This refactor does not add multi-concept score fusion, ontology expansion or
resource exclusions. Semantic matches remain candidates. Existing feature-location,
region-variant and region-association routes and flank conventions are preserved.
ADSP filtering remains a frontend equality filter on already retrieved records;
regional variants retain table presentation even for one record. Paging remains
in the ASK TODO; do not fetch extra pages or add paging commentary.

Focused protocol regressions use recorded APOE evidence and simulated SDK exchanges,
not live LLM reasoning. The annotation regression covers the real /ask streaming
boundary: direct gene/association retrieval without a planner, optional planning
after resolution, and invalid planning preserving earlier evidence. They cover dependent calls, exact transcript scope,
clarification, unsupported capabilities, per-call evidence and bounded termination.
They were added but not executed under AGENTS.md's explicit-request test rule.
Static checks cannot establish live interpretation quality or grounding.

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
| ASK_DEADLINE | 90 seconds of active work per query, maximum 120; announced provider backoff waits are excluded |
| ASK_TELEMETRY | false; enables optional Logfire instrumentation |
| LOGFIRE_TOKEN | Logfire project write token; required for direct API telemetry and answer feedback; supply through the API runtime environment |
| ASK_CAPTURE_CONTENT | false; explicitly opt in to model/prompt/tool content capture |
| ASK_FEEDBACK_ENABLE | false; explicitly enables answer feedback when Logfire telemetry is available; runtime samples set TRUE |

Completed ASK responses include a signed `feedback_reference` when feedback is
available. The client submits it with a `rating` (1 for helpful, 0 for unhelpful)
and an optional `comment` (up to 2,000 characters) to `POST /ask/feedback` through
its same-origin proxy. Explicitly submitted comments are sent to Logfire even
when model-content capture is disabled. Feedback is recorded as
`gen_ai.evaluation.result`, named `user_helpfulness`, linked to the original
response trace. A 204 response confirms acceptance for telemetry export, not
remote delivery. The signing key is derived automatically from the server-side
Logfire token using a feedback-specific HMAC label; no separate signing-secret
setting is needed. Workers using the same Logfire token share the key across
deployments. Rotating that token invalidates existing feedback references.
No feedback or conversation records are stored by the application. The UI allows
one successful submission per answer in the current session; this is not a
server-side deduplication guarantee.

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
entrypoint and point the frontend's `API_INTERNAL_URL` at that running application.

## What is connected and what is pending

- Tools call existing gene, variant, and track record operations, gene structure,
  and gene/variant associations. They consume the API's list-based `RecordResponse`
  data, bound response bytes/rows, and report retrieval failures. Variant lookups
  accept refSNP, structural, and positional allelic identifiers. Association tools
  retain the existing `page` and `flank` parameters and API page-number limit.
- Gene/track semantic query endpoints now generate query embeddings through
  OpenRouter before invoking their existing retrieval methods. The agent sends
  search text and never receives or generates the vector. Variant semantic search
  remains planned. The parameter is `text`, for example
  `/query/tracks?text=Alzheimer+disease`; the ASK `search_resources` tool also
  accepts `text`.
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
- For identified genes, association trait summaries support phenotype mapping with
  source/page/query context. Unseeded phenotype-first requests need scope
  clarification; semantic similarity is not association evidence. Further work is
  recorded in developer-notes/TODO.md.
- `get_gene(content="full")` retrieves curated association evidence from
  `memberships.curated_lists`. The model-facing `gene_evidence` summary retains
  each listing's assertions, qualifiers, evidence codes and provenance, plus
  `associated_with_known_ad_locus` when returned. Summary lookup remains the
  default. Curated evidence stays distinct from regional variant associations;
  missing evidence does not establish absence of association. AD-related GO and
  pathway evidence remains deferred in developer-notes/TODO.md.
- API help uses FastAPI's OpenAPI generation for the registered routes. Its
  operation catalog preserves `x-status` for planned endpoints. Its
  operation catalog does not depend on application-level server metadata, which
  currently prevents the full legacy `/openapi.json` export from validating.
  Existing application metadata and its factory were not changed to repair that
  unrelated refactor issue.

## Response contract and extension points

ASK streams text/tool events and a final data-niagads-result part with envelope
version 4. Results retain entity/annotation/content, authoritative rows, source
IDs, parameters, warnings and pagination. The agent sees previews/field names and
association trait summaries; it never supplies a replacement dataset.

Presentation entries contain intent, not frontend adapter/component identifiers:

```json
{
  "result_id": "<returned result ID>",
  "view": "plot",
  "title": "Association counts by track",
  "plot_type": "bar",
  "group_by": "track",
  "x": null,
  "y": null
}
```

The present_results tool accepts this as its presentation argument. view is
 auto/table/plot; plot_type and field hints are optional open strings. Python
validates the structure and result reference. It does not decide which UI can
render the data. Explicit table/plot requests must be recorded; auto leaves the
choice to the client. Unsupported requests are explained by frontend adapters,
with raw data/provenance retained. Versions 2 and 3 are not accepted by this client.
Update the paired API and client together.

All UI source-to-component mappings, column definitions, filter choices, chart
eligibility and layout live in the frontend app/ask/translators library. This
follows the Charts package's source-format translator pattern. To add or change a
view, implement/register a frontend adapter for the expected API output; no Python
UI registry or capability export needs updating. The API remains responsible for
its canonical record contracts and evidence integrity. Retrieval operations stay
in ask/operations.py with their existing API response models.

Data enums alone are shared through the existing exporter. Regenerate them only
when these domain enums change, not when UI adapters change:

```bash
PYTHONPATH=components:bases python -m niagads.open_access_api.ask.export_types \
  ../niagads-viz-monorepo/apps/open-access-api-client/app/ask/types.generated.ts
```

The frontend config NEXT_PUBLIC_ASK_MAX_BAR_CATEGORIES controls bar cardinality
(default 7, positive integer). This display policy is no longer a Python setting.
Histogram filters stay disabled; categorical/boolean controls and track selection
are UI-owned. API aggregate counts retain their values; loaded-row counts are
labelled as such. Regional Manhattan/standalone pies remain follow-up adapters.

History is browser-memory only and cleared on reload/new session. At most 12
messages/16,000 text characters enter a run; the request body is capped at 64 KiB.
Client-submitted tool results/datasets are discarded, and only user/assistant
text is allowed. Follow-up evidence is re-fetched. There is no Valkey/Cognito
integration or cross-visit persistence in these branches.

ASK handles failures at two boundaries:

- Before streaming, setup failures raise `RuntimeError` with the original cause.
  The existing FastAPI runtime handler returns the diagnostic detail, traceback,
  and issue-reporting instructions. Invalid conversation input uses HTTP 422/413.
- For unrecovered failures after streaming starts, the SDK emits an error event containing the exception
  message and request reference. Server logs retain the chained traceback.
  Retrieved evidence is sent before the error event when available.

API retrieval requests JSON. HTTP 404 is a no-match result; other failures raise
`RuntimeError` with the API's response details. Unsupported capabilities remain
ordinary tool notices in the result envelope's `issues` list. Native errors remain
intact; targeted token-limit recovery and provider retries are described below.
The frontend forwards API error responses and displays streamed error messages.
Logfire remains optional and retains exception messages and tracebacks.
Internal API deadlines enforce `ASK_API_TIMEOUT`; `ASK_DEADLINE` bounds active
work in the run. Provider backoff waits pause that deadline.

## OpenRouter retry progress

The configured ASK_MODEL is unchanged. One shared helper wraps planner requests
and the opening of evidence streams. It retries only HTTP 429/500–599 or those
codes in native OpenRouter error envelopes, including HTTP 200 JSON/SSE errors.
It makes at most five attempts, waiting 5/15/30/60 seconds plus 0–1 second jitter.
A valid Retry-After (seconds or HTTP date) replaces that delay. SDK implicit retries
are disabled. Each retry logs attempt/status/wait; exhaustion re-raises the native
final error. Streams already delivered to the caller are never replayed.

Request-local transient data-niagads-model-status events report requesting,
waiting, retrying and failed, with attempt and waitSeconds. Explicit null clears
progress when a response arrives. These events are not evidence or chat history.
The UI reuses LoadingSpinner with a live countdown and shows the friendly busy
notice/Retry button on exhausted retries, retaining expandable native diagnostics.
Manual Retry resubmits the last question, preserving prior chat/dashboard results.

Backoff excludes sleep time from the existing active-work deadline, as approved.
Stop/disconnect cancels the pending request/wait. The proxy retains a 100-second
connection/header timeout, then relies on the backend's active-work deadline and
client cancellation. Its former 100-second body timeout/120-second duration hint
would prevent the requested schedule and are removed. SSE heartbeats keep the
waiting stream active; deployment/reverse-proxy limits must also permit these
longer streams. No dependencies, embeddings, semantic retrieval or model routing
settings change.

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


## Phenotype annotations for queried genes

For a known gene or named candidate genes, use get_gene_associations and its
returned trait annotations to map the queried genes to reported phenotypes. Tool
summaries expose association_traits (context, original term/CURIE and source
tracks), with association_query containing the original gene/flank scope. Full
and summary content retain these annotations; API association counts are not
recomputed. These terms describe the retained rows/pages, not an exhaustive set
of phenotypes or proof that a gene causes a phenotype. Missing annotations do not
prove absence of association. Keep disease and population contexts distinct.

The former unconditional find_phenotype_genes unavailable placeholder was removed.
Without identified candidate genes, clarify scope instead of claiming an
exhaustive phenotype-first search or treating semantic matches as associations.
