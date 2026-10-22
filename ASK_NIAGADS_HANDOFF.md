# ASK NIAGADS local Codex handoff

## Current task: incremental dependent execution — 2026-10-22

Continue on `codex/ask-stepwise-execution`, created from updated `refactor/api`
415ccad9. Paired frontend branch has the same name, based on app/oa-api 82feb577.
This supersedes historical branch pointers below; variants-by-region is now in
both development bases and remains preserved.

The existing PydanticAI loop executes dependent actions. QueryPlan now carries a
bounded goal, flat concepts, short constraints, unresolved scope and necessary
clarifications/evidence hints, without a recursive tree or tool sequence. The
preliminary interpretation call remains; both calls keep max_tokens=2000 and the
same shared budgets/deadline/retries. No new executor, provider or dependencies.
Gene/structure evidence_fields can be selected per call; structure summaries now
expose transcript identities/spans without needing upfront prediction. Exons stay
opt-in. clarify_request records the existing clarification status while retaining
retrieved evidence. Native unsupported outcomes and brief-response rules remain.

Frontend strict validation and generated enums match the new interpretation;
deploy both repos together. Result envelope v4, UI adapters/downloads, feature
location and regional routes, +/-10 kb defaults, typed ADSP filters, one-record
regional tables and omission of invalid SSE null fields are unchanged. No paging
implementation or commentary; ASK pagination TODO remains.

Focused regressions added for real recorded gene evidence and simulated native
SDK dependent exchanges, exact transcript scope, clarification, unsupported tools,
per-call annotations and request/tool/deadline termination. Tests NOT RUN:
Backend AGENTS.md allows execution only on explicit request. The paired frontend
rules permit tests: all three new interpretation-contract regressions pass.
Static AST/JSON-schema/tool registration, Black/isort, frontend TypeScript/ESLint/
Prettier and diff checks pass.
Black reports its existing Python 3.12 / target 3.13 warning; AST parses on 3.12.
No live API, database, model or browser validation; no incident diagnosis.

Next: explicitly authorized focused tests and local live model/API review. See
`developer-notes/plans/ask/stepwise-execution.md` and the updated ASK guide.

## Current task: variants-by-region base merge — 2026-10-21

Continue on feature/variants-by-region in both repos. This supersedes historical
branch pointers below. Backend merged origin/refactor/api at 72db9575, preserving
feature-location resolution, regional variant retrieval and ADSP equality-filter
presentation intents alongside compaction, token recovery and OpenRouter retries.
The only code conflict was agent instructions; both behaviors were retained.

The remote feature branch advanced to f6ce80dd during the merge; its variant
record positional_id visibility change was merged without modification.

62 focused offline ASK context/limit/retry/tool checks pass, using recorded gene
fixtures without API-app/database startup. Syntax, Black/isort and diff checks
pass. Four SDK legacy-httpx deprecation warnings remain. No DB, ORM or live-model
validation was attempted. Feature-owned region routes/service/ORM changes were
preserved, not rewritten. Frontend is being merged from app/oa-api separately.


## Development-base integration — 2026-10-21

Merged refactor/api at 2497a296 into codex/ask-context-recovery-retries. Keep base
complete-page retrieval and region-service changes, curated-list/known-locus gene
evidence, semantic fallback only after a gene lookup has no matches, and relaxed
planner handling of independent retrieval. Selective annotations, compaction,
token recovery and OpenRouter retries remain. Frontend is unchanged by this merge;
its paired base must include the complete-page contract changes for large pages.
Historical verification and uncommitted-state notes below predate this merge.
56 isolated context/limit/retry/tool checks pass without DB/model calls. The SDK
streaming compaction check uses repeated completed exchanges; its production size
guard is unchanged. Latest retry UI uses loading/countdown and a brief final
OpenRouter Alert without retry diagnostics. See CHECKPOINT.md for merge details.

## Current branch — 2026-10-21

The user requested moving this work to feature branches. Continue on
`codex/ask-context-recovery-retries`, created from `refactor/api` in this repo.
The same feature branch name is used in both repositories. All pending
context compaction, token recovery and OpenRouter retry changes were
preserved. The user subsequently authorized committing and pushing both
feature branches. Earlier notes describing uncommitted work are historical.
This supersedes instructions to work on development bases, avoid new
branches, or leave this work uncommitted.

## OpenRouter retries and progress — 2026-10-21

Configured ASK_MODEL now uses the shared bounded retry helper for planning and
stream opening: four retries on 429/5xx only, 5/15/30/60 seconds plus jitter,
Retry-After precedence, native final errors preserved. Request-local transient
status events drive the frontend countdown/Retry UI; null clears on response.
The user approved pausing the existing active deadline during waits. The proxy's
fixed streaming timeout is removed; Stop still cancels. Partial delivered streams
are not replayed. No dependencies, embeddings or semantic retrieval changes.

45 focused backend checks and eight client regressions pass; types/lint/format
checks pass. Browser verification remains pending because the existing dev server
was unresponsive and prevented a second server. No live provider/database calls.
Read CHECKPOINT.md and the API guide's retry section for implementation details.
Changes remain uncommitted on the current development bases.

## Token-limit recovery — 2026-10-21

Approved follow-up adds status=token_limit and usage_limit diagnostics to the paired
v4 contracts. Planning/mid-stream token exhaustion preserves retrieved records and
presentation references, emits a brief deterministic summary/follow-up suggestion,
and closes normally with finishReason=length. No extra model call or higher budget.
The UI marks results incomplete and collapses native error details; existing default
dashboard adapters and downloads work even without an agent presentation.

See CHECKPOINT.md for focused recorded-data/protocol tests and remaining local
validation. Deploy both repos together. Other limit/provider errors keep their
existing error flow. Work remains uncommitted on the current development bases.

## Working context implementation — 2026-10-21

The approved revision is implemented and left uncommitted on refactor/api, paired
with the GeneEvidence planner schema on frontend app/oa-api. Read CHECKPOINT.md
and developer-notes/plans/ask/compact-working-context-review.md first. They
supersede the old boolean structure-toggle plan and paused-task instructions.

Run-local ProcessHistory compaction preserves authoritative evidence, complete
records, page/scope metadata, unresolved/retry exchanges and native diagnostics.
Gene lookups remain brief by default; explicitly needed full annotations and
selective transcript/exon summaries are available. Existing budgets and cross-turn
re-fetch behavior remain. This does not add cumulative evidence across requests.

Sixteen recorded-data/protocol/SDK-streaming checks pass without database/model
access. Client type checking and targeted lint pass. Local real API/OpenRouter
usage and grounding validation remains; source changes are not a deployed backend.

Earlier sections below are historical unless they describe unchanged behavior.

## Error heading correction / association task status — 2026-10-21

Frontend SDK/stream errors now get a short unexpected-error heading instead of
raw diagnostics. FastAPI user-facing messages, references and reporting guidance
remain visible; technical detail and traces remain in collapsed sections. Eight
focused error tests passed. This does not fix the malformed stream in the user's
screenshot.

ASK retrieval now retains complete non-query FastAPI pages, including responses
over 1 MiB, with row/source/limit caps removed from paired contracts. Query/search
caps remain. Pagination still reflects FastAPI's pages (DEFAULT_PAGE_SIZE=5000),
not automatic fetching of every page. Backend error regressions: 12 passed;
Black/isort/diff checks passed. Added a real-API full-page comparison in
test_transport.py, not run because live verification was stopped by the user.
Dashboard source changes are implemented; browser/real-data validation is pending.
The user is running the API on the host. Compaction work remains separate.

## Error reporting guidance — 2026-10-21

Frontend-only changes in niagads-viz-monorepo: ASK Chat now links help@niagads.org
and the existing API GitHub issue tracker, explains that reports should include
error details and a request reference when present, and exposes the complete
received error in an expandable details block. FastAPI detail AND message are
retained, restoring visible GitHub/admin instructions hidden by the formatter.
Python handlers and proxy forwarding already preserved the response; neither was
changed. If FastAPI never initializes, no backend response/trace exists to show;
the proxy reference belongs to its Next.js log entry.

Stack traces use a separate nested, initially collapsed "Stack trace" section
with readable frame lines; other response fields use formatted JSON. A missing
backend trace does not produce an empty trace section.

Seven focused frontend error tests, targeted ESLint, app TypeScript and diff
whitespace checks passed. No browser/live outage validation or backend rebuild.
Compaction remains assigned to the user's separate handoff and was not resumed.

## Current task: chat and temporary dashboards

Continue on codex/ask-chat-dashboard-navigation from updated refactor/api. The
paired frontend branch starts from app/oa-api. Canonical plan/progress:
developer-notes/plans/ask/chat-dashboard-navigation.md. ASK report tools request
existing brief/summary models and chat is instructed to stay brief. UI adapters
remain frontend owned; v4 is unchanged. Frontend ASK_CHAT_DASHBOARD.md describes
temporary IDs, same-tab navigation, summary Cards and raw downloads. Earlier
checkpoints below are historical. No synthetic tests or live database/model calls.

## Current task: query planning integrated with dashboard v4

Work is on codex/ask-structured-query-planning in both repositories. The user
merged and deleted the dashboard branches. Updated development bases are merged
here: Python refactor/api at dc5c41eb and frontend app/oa-api at c608799b.
Do not resume from the historical dashboard branches mentioned below.

The ASK planner still runs before tool selection, using ASK_MODEL and shared
request/token/deadline budgets. Its validated data-niagads-plan stream is separate
from authoritative data-niagads-result v4. The UI retains the plan disclosure,
dashboard tables/bars, track-selection action, source/page metadata and native
diagnostics. Python exports domain and planning enums, never UI adapter rules.
Explicit table/plot preferences remain presentation intent; frontend adapters own
rendering and eligibility. Clarifications and deferred exclusions pause retrieval.
Direct /query endpoints and semantic retrieval behavior remain unchanged.

The planner's get_track_data remains a location-aware placeholder; the dashboard's
manual selected-track fetch uses the existing parameter-free track-data route.
These are distinct flows. Wiring genomic location-aware agent retrieval is a
follow-up, not part of this merge.

Synthetic planning tests were also removed to carry forward the user's rejection
of toy-data validation. Existing dashboard test removals are preserved. Real API,
OpenRouter and browser behavior remain unvalidated; no tests/live calls were run.
Merge checks passed: Python parse/import/schema/Black/isort, frontend TypeScript
and targeted ESLint, and focused diff whitespace checks. See the Python ledger
at developer-notes/plans/ask/structured-query-planning.md.

## Previous dashboard checkpoint (historical)

## Validation correction: synthetic tests removed

At the user's request, synthetic-record ASK dashboard, presentation-intent,
track-data and phenotype-mapping tests have been removed in both repositories.
The frontend test:ask command and obsolete synthetic smoke-run instructions were
also removed. Live integration tests and unrelated diagnostic tests remain.
Earlier test references below are historical and do not establish real-data
correctness. Static checks establish source consistency only. Validation against
actual API responses, databases and model behavior remains pending; no tests or
live requests were run for this removal.

## Current boundary: frontend-owned adapters (v4)

Work continues on codex/ask-dashboard-translators in both repos after the
2026-10-21 development-base merges. Query-planning branches remain separate.
The user rejected Python-owned UI mappings and approved this refactor.

Python returns authoritative results, provenance/query/pagination and coarse
PresentationIntent: result_id, view (auto/table/plot), title, optional open-string
plot_type/group_by/x/y hints. It validates intent shape and run-local result IDs.
It owns no adapter registry, column/filter definitions, chart eligibility or chart
limits. ask/presentations.py and exported table rules are removed. Result summaries
expose actual API field names; phenotype association summaries are preserved.

Frontend adapters in app/ask/translators own expected source formats, typed table
props and categorical bar conversion. Changing components/columns/filters requires
no Python change. Auto defaults to a supported table; explicit table requests stay
tables. Plot preferences select local adapters or produce an explanatory notice
with raw results retained. Unsupported plot types, axes or groupings are not
silently rendered as another view. Plot-name strings are not executable code.
Only currently implemented tables and bars are enabled; regional Manhattan and
standalone pie remain follow-ups. Track selection/fetch, scientific p-value strings,
Card/Alert styling, source/query/page/partial-failure details remain intact.

The bar limit is now frontend NEXT_PUBLIC_ASK_MAX_BAR_CATEGORIES (positive integer,
default 7); ASK_MAX_BAR_CATEGORIES is removed. Histogram filters remain disabled.
Breaking protocol revision: envelope v4 replaces v3 UI selections with intent;
update paired backend/frontend together. No v3 fallback is introduced.

Plan/ledger: developer-notes/plans/ask/frontend-presentation-adapters.md in Python.
Synthetic-record tests were removed at the user's request. No live model/database
calls, SQL/ORM/ETL/retrieval/embedding changes or dependency installs. Final static
verification passed: Python AST/Black/isort and response/tool schema generation;
frontend TypeScript and targeted ESLint; both git diff --check. Independent review
found an explicit-axis mismatch, now fixed; its synthetic regression case was
removed. Details are recorded in that plan.

## Prior dashboard checkpoint (v3; superseded)


Work is on **codex/ask-dashboard-translators** in both repositories, based on
Python **refactor/api at ef6d2ba1** and frontend **app/oa-api at c3962e5f**.
The separate codex/ask-structured-query-planning branches are preserved. Their
planning implementation is not included in these bases and was not modified.

The user approved the contract proposal in
`developer-notes/plans/ask/dashboard-translators.md`. ASK now uses envelope version
3: presentations select a registered translator, result_id and typed parameters.
Deploy/update the paired backend and client together; version-2 selections are
not silently reinterpreted. Server-owned rows/provenance/pagination are retained.

Registered tables cover search matches, gene/variant/track records, associations
and association counts. Python advertises/validates compatible selections and
exports mapping rules; deterministic TypeScript translators construct table/bar
props. The agent neither rewrites records nor computes aggregates. Unknown nested
structures remain in raw records. Results without a compatible panel also retain
their raw records and provenance in the UI.

Categorical/boolean table filters reuse existing controls. Numeric/p-value column
filters are disabled because histogram filters are excluded. Reported scientific
p-value strings are preserved without numeric underflow; censored/nondecimal
strings remain displayed with p-value sorting disabled for that dataset. Decimal
p-value sorting is implemented without floating-point conversion. The separate
negative-log10 field remains numeric.

Standalone bars are independent of table filters. category_counts_bar counts
loaded rows by a registered scalar field; association_counts_bar displays API
num_associations without recounting. Scope labels and completeness warnings remain
visible. ASK_MAX_BAR_CATEGORIES defaults to 7; larger sets keep all counts in the
table without truncation or fabricated Other categories. Table filters retain
their existing category policy. No standalone pies or shared panel state.

Verification: app TypeScript/targeted ESLint and Pydantic v3 JSON schema generation
passed. Table source TypeScript passed with --ignoreDeprecations 5.0 overriding an
existing config value unsupported by the installed compiler. Final checks and
independent review are recorded in the task plan. Test cases were added/updated
but not executed under AGENTS.md; no live model/database requests were made.
Rebuild the workspace Table package before local UI review to pick up p-value
preservation changes. Retrieval, SQL/ORM/ETL and embedding behavior are unchanged.

Next: local integration review. Deferred: table histogram repair, regional
Manhattan with position/-log10(p) and disease/population grouping, cross-panel
filtering. Resume from these branches, not main or the historical branches below.

### Track selection and data fetch

Track search and track-record tables enable checkboxes and **Fetch selected track
data**, with at most five selected tracks. The reusable Table option is
`rowSelectOpts.maxSelectedRows` (positive integer; omitted means unlimited).
Unchecked rows are disabled at the cap; selected rows can still be deselected,
including across pages/filters. Bulk updates cannot add beyond the cap.

The client action POSTs selected IDs to `/api/track-data`. Its server-side proxy
calls exactly `/record/track/{track_id}/data` for each ID in parallel using API_INTERNAL_URL,
with no query parameters or LLM request. The upstream endpoint is now included from the merged development base; it was
not tested against a live API here. IDs are
validated/encoded; authentication forwarding follows the existing ASK proxy.

Each action appends an independent association table below its source track list.
A Requested track ID column preserves endpoint provenance separately from any
reported track field. Per-track successes, empty responses, failures, request
references and original response metadata remain visible. Pagination stays
per-track; omitted pagination means unknown completeness. No combined database
total or complete-result claim is invented. Local action tables use the shared
translator data interface without applying the bounded LLM envelope's row cap.
Fetched records remain in the current UI session and are not sent into chat
history or accepted as model evidence. Numeric histogram filters stay disabled.

Synthetic action tests were subsequently removed at the user's request.
Historical static checks: App and Table source TypeScript and targeted app ESLint
passed; independent review found no actionable defects. The Table workspace bundle/declarations built
successfully using a temporary compiler compatibility override, with existing
circular-import/external-dependency warnings. No repository build configuration
changed. No live model/database calls were made.

### Gene-to-phenotype evidence correction

Removed the unconditional find_phenotype_genes placeholder and its misleading
unavailable notice. For a known gene or named candidate genes, ASK uses existing
gene-association retrieval and interprets the returned trait annotations.
Association tool summaries now expose deduplicated context, original term/CURIE
and source tracks across all retained rows, not just the five-row scalar preview.
The gene/flank query, page, has_more and warnings remain available to the agent.
This also supports inspecting trait annotations from API count-summary rows
without recalculating their num_associations values.

Population/ethnicity contexts remain distinct from disease/phenotype annotations.
Missing trait annotations do not prove absence of association; nearby variant
associations do not establish a causal gene relationship. Without candidate genes,
ASK clarifies the gene/search scope rather than claiming an exhaustive inverse
search or substituting semantic similarity as association evidence. No new data
endpoint, SQL/ORM/ETL, embedding, query-planning or model configuration was added.

Synthetic association-trait cases were subsequently removed at the user's request.
Python syntax/style/tool-schema checks and repository diff checks passed;
independent targeted static review found no high-confidence defects. Tests and
live model/database requests remain unrun under the existing policy.

### Development-base merge — 2026-10-21

Merged refactor/api at 4fe3a8de into the Python dashboard branch and app/oa-api at
7d21bf3e into the frontend dashboard branch. Existing dashboard translators,
five-track selection, fetched-data tables and phenotype-mapping fix are retained.
Frontend conflict resolution preserves the base's Card/Alert styling and dashboard
result grouping/raw provenance. The track-data proxy now follows API_INTERNAL_URL
and /record/track/{track}/data, matching the merged API route. The Python TODO
relocation is retained; dashboard follow-ups moved to developer-notes/TODO.md.

Validation: merged Python syntax and ASK response/tool schemas passed; the
ASK transport passes Black/isort. Independent merge review found no actionable
issues. The UI workspace package rebuilt with the existing temporary compiler
compatibility override; its build emitted inherited deprecated-module/type and
bundling warnings. Full API-client TypeScript and targeted ESLint passed after the UI rebuild. Tests and live
model/database calls remain unrun. Incoming unrelated whitespace was preserved;
focused dashboard diff checks relative to the new bases pass.
No changes to query-planning branches.

## Merged prototype checkpoint (historical)

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
- [Deferred work](developer-notes/TODO.md)
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
