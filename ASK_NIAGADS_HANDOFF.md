# ASK NIAGADS local Codex handoff

Updated: 2026-10-20. This document records the current implementation and user
decisions. Use it with each repository's AGENTS.md and the linked run guides.
Earlier design documents contain superseded scope decisions; this handoff and
the user's subsequent instructions take precedence for continuation.

## Checkouts and current work

| Repository | Task branch | Development base | Latest implementation commit |
| --- | --- | --- | --- |
| NIAGADS/niagads-pylib | codex/cloud-environment-setup | refactor/api | c1b1e53c |
| NIAGADS/niagads-viz-monorepo | codex/cloud-environment-setup | app/oa-api | a6cf7519 |

Both task branches are pushed to origin. The Python branch includes refactor/api
through dd191fa9, merged in fcad583a. No task work was based on main, and nothing
was merged back into the development branches. Fetch the task branches, inspect
local changes, and preserve them. Do not reset local work or switch to main.

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
  adapter requests one vector, checks the response model and finite/nonzero
  vector, normalizes it, then passes it to existing ORM retrieval methods.
  The agent does not generate vectors or database queries.
- Region associations remain a contract-compatible HTTP 501 placeholder with
  x-status: planned. Transcript tools resolve an exact transcript's span before
  requesting that region. Phenotype-to-gene retrieval and variant semantic search
  remain unsupported/planned.

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
ASK_API_URL=http://127.0.0.1:8000
```

Adjust that URL to the actual API address. OpenRouter credentials stay on the
Python server. The user has created an OpenRouter account; no real key was
provided to this cloud session and no live inference was performed here.

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

Current model-setting changes passed Python syntax, Black/isort and diff checks.
Test cases were updated but have not been executed since the new explicit-request
rule. Live OpenRouter inference, exact model availability/response conventions,
stored-vector compatibility, database-backed results and Logfire export remain
unverified. Do not describe the application as verified end to end.

Historical checks on 2026-10-19 passed 36 targeted Python tests, six client tests,
client type-check/lint/build and desktop/mobile browser checks using mocked API
and model data. Those results predate the latest embedding/model-setting changes
and do not establish correctness of the current live integration.

For local continuation:

1. Read AGENTS.md, this handoff and the run guides. Inspect both task branches and
   install from their current manifests/locks using the documented workflow.
2. Confirm the required environment variables are set without printing values.
   Preserve the existing database/cache and API startup configuration.
3. When the user explicitly requests validation, start with the guide's real
   embedding-only command. It contacts OpenRouter but requires no database or
   API startup. Confirm the exact model works before attempting semantic search.
4. Run requested focused integration tests using the configured services. Verify
   direct record lookups, gene/track semantic retrieval, provenance, pagination,
   failure handling and the final browser stream. Unsupported flows must remain
   explicit rather than appear as empty successful results.
5. If the supplied embedding ID is rejected or response/encoding compatibility
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
- [Deferred work](TODO.md)
- [Frontend guide on the task branch](https://github.com/NIAGADS/niagads-viz-monorepo/blob/codex/cloud-environment-setup/apps/open-access-api-client/README.md)

Suggested prompt for the next local Codex session:

> Continue ASK NIAGADS from ASK_NIAGADS_HANDOFF.md in both repositories. Read
> AGENTS.md and the run guides first. Use the existing codex/cloud-environment-setup
> branches, preserve local changes and the agreed model settings, and help me
> review the current prototype. Do not implement deferred database/ORM work or
> introduce new model-selection behavior without discussing it with me.
