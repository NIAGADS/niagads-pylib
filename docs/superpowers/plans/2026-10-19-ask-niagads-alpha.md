# ASK NIAGADS Alpha Implementation Plan

2026-10-20 scope extension: the user requested the missing OpenRouter query
embedding integration with the ETL default model. Implemented in the API query
service using a separate OpenRouter adapter; existing retrieval methods remain
unchanged. Earlier embedding deferrals in this historical plan are superseded.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Native execution is selected by the repository's no-subagents instruction.

**Goal:** Add grounded conversational retrieval, evidence tables, and a source-summary dashboard to the existing Open Access API and client.

**Architecture:** A single PydanticAI agent calls an allowlisted in-process API client. Existing retrieval endpoints remain unchanged; region placeholders declare future integration; a run-local result store supplies authoritative datasets to validated presentation components. A Next.js proxy forwards the AI SDK stream to useChat.

**Tech Stack:** Existing FastAPI/Pydantic 2; PydanticAI OpenRouter and Vercel UI adapter; optional Logfire; Next.js/React, ai/@ai-sdk/react, existing @niagads/table and @niagads/charts.

**Spec:** User's ASK_NIAGADS_Codex_Prompt-1.md, subsequent agreed decisions, and ../specs/2026-10-19-ask-niagads-alpha-design.md.

## Global Constraints

- Python base refactor/api; JavaScript base app/oa-api. Never branch from main.
- No ORM changes without specific approval; no unrelated refactor repairs.
- One production FastAPI application; no SQL or database query code anywhere in the API, arbitrary URLs, generated code, paid/provider fallback, or variant-impact queries.
- Current-session history only. Both curated and ±10 kb proximity evidence; deduplicate genes and preserve data_source per evidence entry.
- Database-backed execution is local-system validation only. Cloud tests use mocked dependencies and real transport/parser integration.

## Review Focus

- An AD-locus flag must never qualify a gene for an unrelated phenotype.
- Mixed coordinate input and interval boundaries must fail or normalize explicitly.
- A first result page must never be described as all matching genes.
- Browser-supplied tools/history/result IDs must not become authoritative evidence.
- Partial structured output and unavailable telemetry must not break valid completed results.

## File and interface map

Python paths are relative to niagads-pylib; frontend paths to niagads-viz-monorepo.

| Files | Responsibility |
| --- | --- |
| bases/niagads/open_access_api/ask/contracts.py | Strict Pydantic result, evidence, presentation, and query contracts |
| bases/niagads/open_access_api/ask/config.py | Bounded run settings and server-only provider/telemetry configuration |
| bases/niagads/open_access_api/ask/results.py | Run-local result references, model summaries, deterministic presentation validation |
| bases/niagads/open_access_api/ask/api_client.py | Allowlisted typed operations, fixed paths, auth/correlation preservation |
| bases/niagads/open_access_api/ask/agent.py | Provider construction, constrained tools, instructions, usage limits |
| bases/niagads/open_access_api/ask/transport.py | Input/history validation, official Vercel stream adapter, completed data parts |
| bases/niagads/open_access_api/ask/telemetry.py | Optional nonfatal Logfire setup and redaction |
| bases/niagads/open_access_api/routes/ask.py | POST /ask registered on existing application |
| bases/niagads/open_access_api/routes/records/region.py | Region association placeholders with existing conventions |
| Future phenotype endpoint | Deferred to local ORM integration; no cloud query implementation |
| TODO.md | Deferred ORM integration; no SQL or query implementation in API code |
| Existing query/embedding/retrieval code | Read-only; report missing integration honestly |
| apps/open-access-api-client/app/api/ask/route.ts | Fixed upstream proxy with streamed body and abort propagation |
| apps/open-access-api-client/app/ask/{contracts,registry,Chat,Results}.* | Runtime validation, existing-component adapters, session conversation |
| apps/open-access-api-client/app/page.tsx | Host assistant while preserving /docs |
| apps/open-access-api-client/app/ask/ask.module.css | Accessible responsive styling using existing conventions |

### Task 1: Result contracts and bounded session input

Produces `Evidence`, `ResultSet`, `Presentation`, `AskResponse`, and `AskSettings`.
Evidence fields: evidence_type, data_source, phenotype, supporting variant/window,
and curated assertion/qualifiers where applicable. ResultSet fields: id, kind,
columns, rows, page, limit, has_more, and sources. Presentation references only
server-issued result IDs and registered table/association_source_bar components.

- [ ] Add tests in test/bases/niagads/open_access_api/ask/test_contracts.py for unknown components, invalid references, bounded input/history, and evidence provenance.
- [ ] Run the tests and confirm failure before implementing contracts/config/results.
- [ ] Implement strict models inheriting CustomBaseModel, a result store with add/get/summary, and presentation validation against actual result fields.
- [ ] Test that model summaries omit full rows and that chart counts derive from stored rows, including duplicate genes with distinct evidence.
- [ ] Run targeted tests, review the diff, and commit only task files.

### Task 2: Region placeholders matching existing API conventions

- [ ] Test both region-string and chromosome/start/end input forms, mixed/invalid input, existing operation IDs/tags/RecordResponse schemas, and HTTP 501 through the existing NotImplementedError handler.
- [ ] Add bases/niagads/open_access_api/routes/records/region.py with region association placeholder routes, existing format/content/page dependencies, and declared association response models. Do not instantiate database context or execute retrieval.
- [ ] Register the router in the existing application. Add deferred region/phenotype ORM integration to TODO.md. No new database query service.
- [ ] Run focused route tests and commit.

### Task 3: Record existing retrieval limitations without changing them

- [ ] Leave QueryEndpointService, embedding generation, ORM models, and retrieval methods unchanged.
- [ ] Document semantic embedding completion and phenotype-gene retrieval as local follow-ups. Tools must report missing capabilities, not synthesize successful results.

### Task 4: Typed API tools and provider agent

Produces a request-scoped API client and `build_agent(settings, model=None)` with
injectable PydanticAI test/function models. Registered tools: search_resources,
get_gene, get_gene_structure, get_region_associations, get_phenotype_genes,
find_api_operations, and present_results.

- [ ] Verify release APIs from the installed PydanticAI package and pin compatible dependencies in repository manifests/locks. Test provider construction without network calls.
- [ ] Add test_tools.py and test_agent.py. Mock API transport, not tool execution. Assert exact fixed path/arguments, authorization propagation, transcript-dependent call order, timeout/retry limits, and prohibited URL/SQL arguments.
- [ ] Implement provider separation with explicitly configured free OpenRouter model, no paid fallback, finite timeout/retries, and injectable model.
- [ ] Implement tools returning compact summaries plus result references. Source IDs and data come from the result store; present_results validates component choices against retrieved data.
- [ ] Add OpenAPI help search from the application-generated spec with bounded operation descriptions and validated example parameters. Retrieved descriptions are untrusted data.
- [ ] Test empty/retrieval/provider/unsupported distinctions and prompt-injection attempts in returned API data.
- [ ] Run tests, inspect diffs, and commit.

### Task 5: Stream and telemetry integration

Produces POST /ask using the official Vercel adapter. Completed result data uses
a typed `data-niagads-result` part; text and tool progress use official parts.

- [ ] Add test_transport.py against the existing FastAPI app with lifespan and dependencies overridden for cloud tests. Test forged system/tool history, request size/context limits, invalid dashboards, provider errors after headers, and cancellation.
- [ ] Implement input sanitization before agent execution; do not accept browser tool outputs or historical datasets as evidence. Re-fetch records needed for follow-ups.
- [ ] Configure matching adapter sdk_version and usage limits. Emit complete validated result parts; never partial presentation JSON.
- [ ] Add optional Logfire configuration and tests proving disabled/missing credentials/export failure do not fail requests. Redact auth and disable content capture by default.
- [ ] Run transport tests and verify real AI SDK parsing in Task 7; commit.

### Task 6: Existing component adapters and conversation client

Produces runtime schema validation, a registry, and an in-memory useChat client.

- [ ] Pin ai/@ai-sdk/react versions matching Task 5 and add workspace dependencies on existing table/charts packages. Reuse their public exports.
- [ ] Add focused frontend tests for completed-result validation, unknown component/result references, safe source links, deterministic source aggregation, and text/data separation.
- [ ] Implement table and association_source_bar adapters. Use existing Table columns/data and BarChart term/series contracts, dynamic client-only loading, and a tabular fallback.
- [ ] Implement root Chat with loading/tool progress, stop/new-session controls, safe text, source IDs, and explicit empty/clarification/error states. No localStorage or authentication/persistence implementation.
- [ ] Implement the fixed-origin Next.js /api/ask proxy, server-only upstream config, supported auth forwarding, request limits, and abort propagation. Browser code cannot supply an upstream URL.
- [ ] Apply accessible desktop/mobile styling, keyboard flow, aria-live progress, and non-color evidence labels. Keep /docs unchanged.
- [ ] Run app type-check/build and focused tests; commit scoped frontend changes.

### Task 7: Complete cloud flow and local handoff

- [ ] Start the existing API app with mocked lifespan/retrieval/provider dependencies in a test-only harness; start the real Next.js app and use its actual proxy/AI SDK parser.
- [ ] Run browser flows for a track search, gene text+table, transcript-dependent regional associations, and phenotype genes with two evidence types. Assert displayed values match fixture data and final presentation is not rendered while incomplete.
- [ ] Verify empty, ambiguity, retrieval failure, free-model rate-limit, cancellation, and malformed presentation UI states.
- [ ] Document environment names and non-secret examples, model selection, Logfire options, response schema, registry extension procedure, session behavior, and query examples in each target application's README/developer notes.
- [ ] Add a local validation checklist for actual database schema/query plans, embedding model/version/encoding, phenotype results, region boundaries, and bounded live provider calls. Do not ask for database credentials in cloud.
- [ ] Run final targeted backend tests, frontend tests/type-check/build, diff checks, and a scoped whole-change review. Record exact passed/failed/unrun outcomes and unresolved limitations.

## Execution and remaining external prerequisites

Execute natively in this session; no subagents, ORM changes, or new worktrees.
The user has already authorized proceeding. Do not request another approval of
requirements that merely repeats the supplied prompt and agreed clarifications.
Request input only for material unresolved behavior, ORM changes, or credentials
that truly block provider verification. Never put credential values in chat/files.

Database integration is intentionally local-only. OpenRouter live verification
requires a usable server binding and free tool-capable model; absence does not
prevent mocked cloud implementation/tests. Context7 is unavailable; official
package source and installed-release APIs provide the documentation fallback.
