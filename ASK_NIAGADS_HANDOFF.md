# ASK NIAGADS local Codex handoff

Updated: 2026-10-20. This document records the current implementation and user
decisions. Use it with each repository's AGENTS.md and the linked run guides.
Earlier design documents contain superseded scope decisions; this handoff and
the user's subsequent instructions take precedence for continuation.

## Checkouts and current work

| Repository | Task branch | Development base | Latest implementation commit |
| --- | --- | --- | --- |
| NIAGADS/niagads-pylib | codex/cloud-environment-setup | refactor/api | c613ea3c |
| NIAGADS/niagads-viz-monorepo | codex/cloud-environment-setup | app/oa-api | c796e7e8 |

Both task branches are pushed to origin. The Python branch includes refactor/api
through dd191fa9, merged in fcad583a. No task work was based on main, and nothing
was merged back into the development branches. Fetch the task branches, inspect
local changes, and preserve them. Do not reset local work or switch to main.
The accidental merge conflicts have been resolved and committed. At this
checkpoint both implementation checkouts were clean and aligned with their
locally recorded origin tracking branches, before these handoff edits. No fetch
was performed to verify remote state. Preserve intentional test-file deletions.

The next task is user review and local integration validation, followed by fixes
to concrete review findings. No additional feature or architecture changes are
requested by this handoff. Discuss significant implementation choices before
applying them; do not silently introduce model selection or compatibility rules.
No further specification approval is pending for the implemented prototype.

## Implemented flow

- Existing FastAPI application exposes POST /ask. One constrained PydanticAI
  agent uses registered HTTP tools and the SDK 7 UI streaming adapter.
- The existing Next.js client proxies /api/ask to the Python API, keeps history
  in the current browser session, and renders validated NIAGADS tables/charts.
- Tools support gene, variant and track identifier lookups, gene structure,
  gene/variant association pages, gene/track semantic search and API help.
- Semantic search sends text to QueryEndpointService. Its OpenRouter embedding
  adapter requests one vector, validates finite/nonzero vector data, normalizes
  it, then passes it to existing ORM retrieval methods. It does not compare the
  returned model identifier with the configured request identifier.
  The agent does not generate vectors or database queries.
- Region associations remain a contract-compatible HTTP 501 placeholder with
  x-status: planned. Transcript tools resolve an exact transcript's span before
  requesting that region. Phenotype-to-gene retrieval and variant semantic search
  remain unsupported/planned.

## Error handling: agreed simplified implementation

- Before streaming starts, setup failures raise `RuntimeError` with the actual
  diagnostic message and original cause. The existing FastAPI runtime handler
  returns detail, traceback, request information, and issue-reporting guidance.
  Malformed/oversized conversation input still uses HTTP 422/413.
- After streaming starts, FastAPI cannot replace the response. Native agent
  errors are logged with their chained traceback, and the SDK emits an error
  event with the original message and request reference. Timeout/transport
  failures outside SDK conversion use the same stream event format. Already
  retrieved evidence is retained when available.
- `api_client.py` explicitly requests JSON. HTTP 404 becomes a no-match result,
  without asking the user to correct an identifier. Other API failures raise
  `RuntimeError` retaining HTTP status and response details. A JSON response
  without `data` is an error, not an empty successful result.
- `RetrievalError`, `QueryEmbeddingError`, the classification/message registry,
  `log_failure()`, and request-local exception capture have been removed. Do not
  reintroduce these layers. Ordinary failures do not need component mixins.
- The tool executor retrieves, stores, and summarizes results without catching
  and reclassifying exceptions. Presentation corrections retain the SDK's
  `ModelRetry` behavior. Unsupported capabilities remain ordinary notices in
  `AskResponse.issues`, not a custom exception taxonomy.
- The Next.js proxy forwards upstream error responses. The browser preserves
  FastAPI detail/request references and plain SDK error messages instead of
  replacing them with generic status-based text.
- Keep Logfire configuration and the diagnostic logging edits for now, as the
  user explicitly requested. Direct OpenRouter export was discussed but no
  switch was authorized. Logfire export itself has not been verified.

## Operation, entity, and serialized-record logic

- Natural-language routes retain `/query` and take the parameter `text`, for
  example `/query/tracks?text=Alzheimer+disease`. The ASK `search_resources` tool
  and query service use `text` as well. `/search` remains the intended namespace
  for structured/exact retrieval; no new `/search` route was added by this rename.
- `ask/operations.py` owns the static `OPERATIONS` registry. `AskOperation`
  specifies endpoint, `Entity`, nullable `AnnotationKind`, and the existing
  `ResponseConfiguration` containing record/response models and content.
- Tools choose registered operation names. `SEARCH_OPERATIONS` derives the
  gene/track semantic-search mapping from registry entries whose record model
  is exactly `SearchMatch`. This exact-class assumption remains in the code;
  it is not a verified general rule for future search types.
- Gene/variant/region association tools select full or summary registry entries;
  retrieval takes the content value from that entry. Result entity, annotation,
  and content also come from the registry rather than model-generated values.
- Python `SearchMatch.matched_record_id` has serialization alias `id`.
  `RecordResponse[SearchMatch]` JSON therefore contains `id`. ASK preserves that
  serialized identifier and merges `matched_record_details` for presentation;
  it no longer requires a `matched_record_id` JSON key or renames it to `id`.
  The Python model field itself was not removed.
- Presentation compatibility remains explicit: tables plus association source
  charts for supported entity/annotation pairs with SUMMARY content. The type
  exporter shares Entity/AnnotationKind/ResponseContent and chart pairs with
  the frontend. OpenAPI help searches GET descriptions; it is not dynamic tool
  registration or model discovery.
- These statements describe the current implementation, not approval of every
  remaining limit, fallback, or entity-specific branch. Continue the review
  instead of adding parallel validation or speculative compatibility logic.

## Model settings: agreed current behavior

Configure these on the Python server, alongside its existing API settings:

```dotenv
DATABASE_URI=your-existing-database-uri
CACHE_DB_URI=your-existing-cache-uri
OPENROUTER_API_KEY=your-server-side-key
ASK_MODEL=openrouter/free
OPENROUTER_EMBEDDING_MODEL=liquid/lfm-2.5-embedding-350m:free
```

These are placeholders, not credentials. Never commit or display secret values.
The cache variable is CACHE_DB_URI. Prefer process environment configuration when
resuming: shared settings honor SERVICE_ENV when choosing an env file, while
AskSettings reads .env relative to the process working directory.

- ASK_MODEL accepts specific chat models or OpenRouter routers, including
  openrouter/free and openrouter/auto. There is no chat-model allowlist.
- OPENROUTER_EMBEDDING_MODEL is a separate environment setting. It defaults to
  liquid/lfm-2.5-embedding-350m:free and currently accepts only that exact value
  through a Pydantic Literal declaration in QueryEmbeddingSettings.
- That validation checks the configured string only. It does not establish model
  availability, dimensions, tokenizer behavior or compatibility with stored data.
- The embedding ID was supplied by the user for the ETL default,
  LiquidAI/LFM2.5-Embedding-350M. Send it directly to OpenRouter. Catalog discovery
  is intentionally off; do not restore it or substitute another model.
- A future embedding change needs an explicit compatibility decision and an
  update to the current restriction. Changing configuration must not silently
  regenerate stored embeddings or introduce model fallbacks.

The frontend uses its own .env.local setting:

```dotenv
API_INTERNAL_URL=http://127.0.0.1:8000
```

Adjust that URL to the actual API address. OpenRouter credentials stay on the
Python server. An earlier key was rejected with HTTP 401 and "User not found";
direct key validation reproduced that failure. The user replaced it and confirmed
the new key works. Never include credentials in checkpoint documents.

OpenRouter returned `openrouter:LiquidAI/LFM2.5-Embedding-350M:free` for the
configured `liquid/lfm-2.5-embedding-350m:free` request. The requested environment
value was being used; a local exact-string comparison caused the failure.
That comparison was removed. The user rejected a hardcoded alias workaround;
do not restore one or change the configured model to match response metadata.

## Boundaries to preserve

- Cloud development will never access the user's database. Live database work
  and validation must take place on the user's system.
- Do not introduce SQL in the API or agent. Do not modify ORM retrieval, ETL,
  stored vectors, schemas or migrations without a separate user request.
  User changes to those files arrived through the development-base merge and
  must be preserved. The authorized embedding change only supplies a vector to
  existing retrieval methods; the ETL embedding generator remains unchanged.
- Keep exact model assignments. Do not resolve failures by silently selecting
  another embedding model, removing its restriction or adding a fallback.
- Respect AGENTS.md: run tests only when explicitly requested. This handoff is
  not itself a request to execute tests. Do not launch subagents.
- Preserve current-session history only. Valkey/Cognito persistence exists on
  other branches and remains a TODO, not part of this prototype.

Future phenotype-to-gene retrieval must combine curated evidence
(associated_with_known_ad_locus and curated_lists) with associations in the gene
footprint plus/minus 10 kb. Deduplicate genes while preserving all evidence and
data_source provenance: curated list versus stable track identifier. Predicted
variant-impact retrieval is deferred. See TODO.md for the remaining work.

## Validation state and next steps

Error-handling changes passed Python syntax, Black/isort and diff checks.
Focused frontend ESLint and TypeScript checks for the changed error/proxy files
passed. Full client typechecking was blocked by missing installed `ai`,
`@ai-sdk/react`, and `@scalar/api-reference-react` dependencies and resulting
type errors. No dependency installation was attempted for that check.
Tests were updated but not run by the agent; no live model or database calls were
made for the simplification. User-reported failures are evidence of specific
problems, not an end-to-end passing result.

Remaining review/validation items:

- The API client still slices `data[:50]`, sets `limit=50`, and adds a truncation
  warning. Both merge versions contained this cap; it was not removed. Backend
  and frontend contracts also retain row/result/preview limits. The user's
  concern about these limits remains open; do not describe them as resolved.
- Normalization remains in the query embedding adapter. Whether OpenRouter
  already normalizes the returned vector is unverified: no raw norm measurement
  completed. Cosine distance is used by the ORM; do not assume provider behavior
  or add more normalization policy without evidence and user direction.
- `developer-notes/plans/ask/validation-and-defaults-review.md` inventories
  validation and defaults with assumptions flagged. It predates the latest
  simplification, so source files are authoritative for current line references
  and removed error machinery. Many non-error limits/defaults still await review.
- `test_transport.py` is a real-service integration smoke test for APOE retrieval,
  stream completion and presentation selection. It does not establish correct
  association counts, page/flank use, answer accuracy, or comprehensive failure
  handling. `test_errors.py` now targets plain runtime failures and no matches.
- Live stored-vector compatibility, database-backed results, final browser
  behavior, and Logfire export remain unverified. Do not claim end-to-end success.

Historical checks on 2026-10-19 passed 36 targeted Python tests, six client tests,
client type-check/lint/build and desktop/mobile browser checks using mocked API
and model data. Those results predate the latest embedding/model-setting changes
and do not establish correctness of the current live integration.

For local continuation:

1. Read AGENTS.md, this handoff and the run guides. Inspect both task branches and
   install from their current manifests/locks using the documented workflow.
2. Confirm the required environment variables are set without printing values.
   Preserve the existing database/cache and API startup configuration.
3. Continue the user's review of remaining client limits and operation/entity
   assumptions. Reuse the existing registry/models; do not restore the removed
   exception classifier, model-name equality check, or hardcoded aliases.
4. Run requested focused integration tests using the configured services. Verify
   direct record lookups, gene/track semantic retrieval, provenance, pagination,
   failure handling and the final browser stream. Unsupported flows must remain
   explicit rather than appear as empty successful results.
5. Make live OpenRouter calls only with authorization for their purpose and
   maximum request count, including retries. If response/encoding compatibility
   fails, report the actual finding and discuss the fix. Do not switch models or
   alter stored data to make a demonstration pass.

## Relevant files

- [API setup and review guide](bases/niagads/open_access_api/ASK_NIAGADS.md)
- [Non-secret configuration sample](bases/niagads/open_access_api/sample.ask.env)
- [Agent settings](bases/niagads/open_access_api/ask/config.py) and
  [provider construction](bases/niagads/open_access_api/ask/provider.py)
- [Embedding settings](components/niagads/api/common/config.py),
  [OpenRouter adapter](components/niagads/api/common/services/embeddings.py) and
  [query service](components/niagads/api/common/services/query.py)
- [Focused tests](test/bases/niagads/open_access_api/ask)
- [Validation/defaults review](developer-notes/plans/ask/validation-and-defaults-review.md)
- [Operation registry](bases/niagads/open_access_api/ask/operations.py)
- [Deferred work](TODO.md)
- [Frontend guide on the task branch](https://github.com/NIAGADS/niagads-viz-monorepo/blob/codex/cloud-environment-setup/apps/open-access-api-client/README.md)

Suggested prompt for the next local Codex session:

> Continue ASK NIAGADS from ASK_NIAGADS_HANDOFF.md in both repositories. Read
> AGENTS.md and the run guides first. Use the existing codex/cloud-environment-setup
> branches, preserve local changes and the agreed model settings, and help me
> review the current prototype. Keep pre-stream RuntimeErrors separate from SDK
> stream errors, preserve diagnostics and Logfire, and do not restore custom
> exception classification. Review remaining result caps and operation/entity
> assumptions against source. Do not run tests or live requests without explicit
> authorization, implement deferred ORM work, or add model-selection behavior.
