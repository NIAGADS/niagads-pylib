# ASK NIAGADS alpha design

Status: prototype specification. User scope correction below supersedes the earlier database implementation proposals.

2026-10-20 update: the user explicitly requested query embedding implementation
through OpenRouter, using the ETL default LiquidAI/LFM2.5-Embedding-350M. This
supersedes the earlier query-embedding deferral below. The API now resolves that
exact model in OpenRouter's embedding catalog, embeds raw query text, normalizes
the vector, and passes it to existing retrieval methods. No ETL, stored-vector,
ORM, or SQL changes are authorized by this extension. Provider availability and
live retrieval remain unverified; see the current ASK_NIAGADS.md run guide.

## Binding scope correction

Build a prototype using existing API operations and mocked responses for cloud validation. No database queries, ORM changes, embedding/retrieval changes, or query-service implementation are in scope. Database queries must remain in the ORM layer, never in API code. Region endpoints may be placeholders matching existing API conventions and returning the existing not-implemented response. Deferred ORM retrieval work belongs in TODO.md and will be implemented locally. The earlier proposed query/embedding implementation sections are removed below.

## Goal and agreed scope

Add a natural-language assistant to the existing Open Access API and its Next.js
client. One constrained PydanticAI agent retrieves evidence using registered API
operations and selects validated text, table, or dashboard presentations. It also
helps users discover endpoints and construct example requests from the API's own
OpenAPI specification. No second FastAPI application, planner agent, MCP server,
AI gateway, generated frontend code, direct agent SQL, or arbitrary URL tool.

Repositories and mandatory development bases:

| Repository | Base | Target |
| --- | --- | --- |
| NIAGADS/niagads-pylib | refactor/api | bases/niagads/open_access_api and shared API components |
| NIAGADS/niagads-viz-monorepo | app/oa-api | apps/open-access-api-client and adapters to existing packages |

Both current task branches are `codex/cloud-environment-setup`. Python starts at
`e2a6625b9a81843a71ad2b9ac4a42b26ca195edc`; JavaScript starts at
`0a9c58fe3e5d2a66d28cb22a64e900eb87beefa7`. Preserve existing work and all unrelated
refactoring. Do not modify ORM models without separate user approval.

Conversation history is current-session only. Valkey/Cognito integration and
cross-visit persistence are deferred; infrastructure exists on other branches.
Variant predicted-impact querying is deferred until its retrieval infrastructure
exists. Both deferrals are recorded in the root TODO.md.

## Initial user journeys and acceptance criteria

1. Research question to datasets/tracks: search the existing API, return bounded
   matches with stable IDs and source metadata; let the user inspect a selection.
2. Gene to annotations and associations: resolve an identifier, retrieve the gene
   and available associations, explain the evidence and show a table.
3. Transcript to regional associations: retrieve gene structure, select a specific
   transcript, derive its span, and retrieve associations in that exact region.
   Ask the user to select when multiple transcripts materially change retrieval;
   do not silently choose a canonical transcript.
4. Disease/phenotype to associated genes: return both curated and proximity
   evidence, deduplicating genes without discarding their supporting sources.
5. API assistance: identify supported endpoints and validated example parameters;
   do not invent endpoint capabilities or claim an example was executed.

The first dashboard combines an existing NIAGADS table with an existing chart
showing association evidence grouped by stable track or curated source. This is
a descriptive summary of retrieved evidence, not a causal ranking. The same
result page supports both components; counts must state whether they describe
the current page or complete server-side aggregation. A table remains available
when chart rendering is unavailable. A regional Manhattan view is a later
registered component unless the initial component inspection makes it the
smaller complete integration.

Example evaluation prompts are templates, not invented domain answers:

- Find datasets related to Alzheimer's disease and show their source IDs.
- Explain the available annotations for APOE and show supporting records.
- Show associations within transcript <returned transcript ID> of APOE.
- Find genes associated with Alzheimer Disease and show how each is supported.
- Which API endpoint retrieves associations for chr19:<start>-<end>?

Evaluate against repository fixtures and deliberate mock results. Do not assign
real expected gene/variant sets without database-backed evidence.

## Repository findings that affect the implementation

- The actual Python base is `open_access_api`, not the hyphenated path in the
  uploaded prompt. Gene structure and association routes already exist.
- The semantic query service currently supplies `embedding = []`. This directly
  blocks genuine semantic search; the prototype must expose that limitation rather than modify retrieval or invent search hits.
- `TextEmbeddingGenerator` exists; it defaults to LiquidAI/LFM2.5-Embedding-350M.
  ETL parameters can override that default. The inspected gene embedding ETL
  normalizes through the generator's default and does not specify prompt_name.
  Stored vectors carry embedding_model metadata, so defaults alone do not prove
  compatibility with the user's database.
- The association ORM accepts OneBasedGenomicRegion, but returns all matching
  rows. Production-scale pagination remains an ORM-layer follow-up. The cloud
  prototype leaves this code unchanged and only caps tool response bytes/rows.
- There is no registered region route. Developer notes already describe using
  the application startup bin-index reference for region lookup.
- Gene fixtures use `memberships.curated_lists`, containing `listing`,
  `assertion`, `qualifier.phenotypes`, study/population qualifiers, and evidence
  codes. Keep these records; do not replace them with model-generated citations.
- Table accepts id/columns/data/options. Charts exposes BarChart with term-indexed
  data and named series keys. Adapters belong in the client app; existing shared
  component contracts remain unchanged.

## Architecture choice

Use typed API tools and server-owned result references. This fits the existing
service boundaries and keeps model-visible summaries separate from full rows.

Alternatives considered: giving the model full datasets would inflate context
and let generated prose corrupt displayed values; direct ORM access from agent
tools would bypass the requested API boundary. Neither is used. Region placeholders declare the future API contract only. All database retrieval remains owned by existing or future ORM methods, outside this prototype.

Flow: Next.js useChat -> same-origin Next.js streaming proxy -> POST /ask on the
existing FastAPI app -> PydanticAI agent -> registered API tools -> bounded API
results -> validated presentation plus streamed explanatory text.

Use PydanticAI's Vercel AI adapter and the matching AI SDK protocol version.
Verify the APIs of the installed release, pin a compatible package set, and test
the stream against the actual client parser. Current upstream adapter source
supports sdk_version 5/6/7, while its prose documentation still emphasizes 5/6;
do not assume prose documentation alone establishes compatibility.

Use PydanticAI's OpenRouter model/provider support where the selected release
provides it. Require an explicitly configured tool-capable free model. Reject
paid model selection and do not silently fall back to another model/provider.
Provider construction is isolated so Bedrock can replace it later without
changing tools, schemas, or component rendering. Bedrock is not implemented now.

## Backend boundaries

New agent modules under the API base separate configuration, provider creation,
tools, contracts, result management, streaming transport, and telemetry.
Serializable API/agent models inherit CustomBaseModel and follow Pydantic 2
conventions. Prefer functions and composition; use framework classes only where
needed. Preserve existing shared behavior rather than introducing agent flags.

Tools have fixed names, typed arguments, documented purpose, and fixed API route
templates. Initial tools search tracks/genes, retrieve a gene/structure, retrieve
gene or regional associations, retrieve phenotype-associated genes, and search
an allowlisted OpenAPI operation catalog. API help is local spec lookup, not web
search. Tools receive no arbitrary URL or raw SQL field.

Reuse existing API clients where suitable; otherwise use request-scoped httpx
with fixed destinations and finite timeouts. In-process ASGI requests may call
registered routes without starting another server. Preserve the incoming
authorization context; forward only required auth/correlation headers and never
trust a browser-provided upstream URL. Do not allow tools to call /ask recursively.

### Region endpoint

Expose a placeholder under /record/region/associations with either region or
chr/start/end input, existing response format/content/page dependencies, and
RecordResponse association/summary schemas. Validate positive one-based inclusive
coordinates. Do not perform bin lookup or retrieval. Valid requests raise
NotImplementedError through the existing handler, returning HTTP 501. Future ORM
integration is a TODO and must not put database queries in API code.

### Deferred retrieval capabilities

Phenotype-associated gene retrieval and query embedding completion are local
ORM/search integration follow-ups, not cloud implementation work. The prototype
must report unavailable capabilities explicitly and may exercise the intended
contracts with clearly identified mocked responses in tests. Retain both evidence
types in the response contract: curated list/known-AD-locus sources and stable
track sources for variants within the gene footprint plus 10 kb. Deduplicate
genes while preserving all evidence. Do not claim mocked results are real.

## Validated response and stream contract

Define a versioned envelope with status, text, results, presentation, sources,
warnings, and request ID. Status distinguishes ok, empty, clarification,
unsupported, retrieval_error, provider_error, and invalid_presentation.
Each result has a server-issued result ID, kind, rows, count/page metadata, source
identifiers, and retrieval parameters. Rows remain authoritative API data.

Presentation is a discriminated union of registered component specifications:
table and association_source_bar initially. Each has a result reference, bounded
component-specific options, and a layout slot. Layout uses a small enum and
ordered slots, never arbitrary CSS, HTML, JSX, or executable code. Backend
validation rejects unknown references, component types, fields, or options.
Frontend independently validates the complete envelope before rendering.

Tool outputs to the model contain bounded summaries and result IDs, not entire
visualization datasets. A run-local result registry owns rows. Deterministic
adapters generate chart aggregates from those rows. The agent may choose a
registered presentation but cannot fabricate datasets or source references.

Stream progress/tool events and explanatory text through the official protocol.
Emit only complete validated structured parts; never render partial JSON as a
dashboard. Explanatory text is separate from result data. Stream failure after
headers are sent is represented as a protocol error; the UI keeps completed
results visible and labels partial/failed responses.

Session history is browser memory only, cleared on reload/new session. Bound
history by message count and text size. Treat returned browser history as
untrusted: reject system roles/attachments and forged tool outputs; reconstruct
permitted user/assistant text. Re-fetch referenced records for a follow-up rather
than treating historical browser result payloads as authoritative evidence.
Cancel outstanding model/API work when the client aborts.

## Limits, configuration, and observability

Initial configurable defaults: 8 model requests, 12 tool calls, 1 model-output
retry, 20-second API timeout, 90-second query deadline, 50 rows per page (maximum
100), 12 history messages, and a bounded total input/body size. Test enforcement
before starting work, including oversized histories, not only after tool returns.
Keep the existing API span policy; do not introduce a conflicting hard-coded
genomic limit. Explain rate limits, unavailable free models, unsupported queries,
no matches, and retrieval failure distinctly.

Configuration examples contain names and non-secret defaults only. OpenRouter
and optional Logfire credentials stay server-side. Telemetry export is off
without credentials. Prompt/argument/result capture is explicitly opt-in and
large datasets/auth headers are never exported. Instrument incoming requests,
agent/model calls, tools/httpx, and validation with a shared correlation context.
Capture timing/errors and usage where exposed by the provider. Observability
failure cannot prevent serving a query.

## Frontend and accessibility

Keep /docs intact; the root route hosts the session conversation. Use ai and
@ai-sdk/react for transport/state, existing NIAGADS controls/styles, and app-local
component adapters. Dynamic client-only charts avoid server hydration problems.
Registry entries map validated component types to React components and declared
contracts; unsupported types show a clear error and preserve available text/data.

Show meaningful tool progress, source IDs, empty/unsupported/error states, stop
and new-session controls. Prose is rendered as text or a safe existing Markdown
renderer without raw HTML. Source links are restricted to trusted API/source
destinations. No model-provided executable URLs or frontend code.

Desktop and mobile use the same reading order: question, explanation, provenance,
table/chart. Keyboard and screen-reader access, visible focus, aria-live progress,
non-color evidence labels, horizontal table scrolling, and a tabular chart
alternative are required. Do not persist chat or results in localStorage. Visual
concept review will precede any substantial new page-layout implementation.

## Validation and delivery boundary

Cloud validation uses deterministic mocked model/API results and existing data
fixtures. Test argument schemas, selected tool execution, dependent transcript
calls, coordinate boundaries, placeholder HTTP 501 behavior, evidence rendering,
pagination, result-reference integrity, stream framing, frontend validation,
and empty/ambiguous/provider/retrieval/cancellation states. Include a browser
flow from the Next.js client through the existing FastAPI route with mocked
retrieval/model dependencies; do not create a second production application.

Use existing package build/type-check/test conventions. Keep tests targeted to
this feature. PydanticAI's test/function models exercise tool execution without
provider credentials. A mocked trace must not be presented as live integration.

The cloud will never have access to the user's database. Do not request database
credentials or attempt live database connectivity. Database startup, phenotype
and region queries against actual schema/data, query-plan checks, embedding
metadata compatibility, and live data-dependent browser validation are local
handoff checks. Bounded OpenRouter verification also requires a usable provider
binding and selected free tool-capable model; do not ask for secret values in chat.

Deliver implementation across both monorepos, config examples, supported query
examples, response/registry extension documentation, targeted test evidence, and
an explicit local validation checklist. Do not claim the full alpha works against
real NIAGADS data until local checks have been completed.

## Technical evidence consulted

- Existing API query/gene routes, association/gene/ontology ORM declarations,
  gene mapping fixture, embedding generator and ETL invocation, Table/Charts
  component source, AGENTS.md, and project-refactor skill.
- Official PydanticAI Vercel adapter source and integration documentation fetched
  from the upstream GitHub repository on 2026-10-19.
- Official AI SDK chatbot/useChat documentation fetched from upstream GitHub on
  2026-10-19. Package registries report pydantic-ai 2.57.0, Logfire 5.2.0,
  ai 7.0.143, and @ai-sdk/react 4.0.147. These are availability observations;
  compatibility and installation are implementation checks, not yet completed.
- Direct documentation-site access was denied by the cloud egress proxy; official
  GitHub sources were accessible. Context7 tools are unavailable in this session.
