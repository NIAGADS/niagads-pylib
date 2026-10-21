# ASK working context — implementation ready for local review, 2026-10-21

## Current branch — 2026-10-21

The user requested moving this work to feature branches. Continue on
`codex/ask-context-recovery-retries`, created from `refactor/api` in this repo.
The same feature branch name is used in both repositories. All pending
context compaction, token recovery and OpenRouter retry changes were
preserved. The user subsequently authorized committing and pushing both
feature branches. Earlier notes describing uncommitted work are historical.
This supersedes instructions to work on development bases, avoid new
branches, or leave this work uncommitted.

This section supersedes the paused-task instructions below. The user approved
compact-working-context-review.md and resumed implementation in this cloud.
Changes remain uncommitted on refactor/api and app/oa-api, without new worktrees
or subagents. No database/OpenRouter requests or Docker rebuilds were performed.

## OpenRouter retry/status follow-up — implemented 2026-10-21

- ask/retries.py contains one shared call_with_retry policy and a thin SDK model
  wrapper for planning/stream-open requests. Exactly 429/5xx, four retries at
  5/15/30/60 seconds plus 0–1 second jitter; valid Retry-After overrides, including
  HTTP-date values. Original final errors/cancellation propagate unchanged.
- provider.py keeps ASK_MODEL, disables implicit SDK retries and installs a small
  response hook retaining Retry-After before the SDK drops headers on body errors.
  This uses the pinned OpenAI HTTP-client hook interface; SDK integration tests
  cover HTTP, HTTP-200 JSON and first-event SSE errors, with header precedence.
  Never replay an already-delivered stream.
- transport.py relays request-scoped transient model status before planning ends,
  plus explicit null on success. Background producer cancellation closes the
  running request; waiting SSE heartbeats contain no evidence. Callback/deadline
  ContextVars avoid storing progress on a shared model instance.
- User explicitly approved pausing ASK_DEADLINE during retry sleeps. Active work
  retains its existing limit. Frontend proxy no longer caps the whole body at
  100 seconds (or advertises 120-second maxDuration); connection/header setup
  retains its timeout. Hosting/reverse-proxy duration limits require matching
  configuration if applicable.
- Frontend model-status.ts, ModelStatusIndicator.tsx, AskSessionProvider.tsx and
  Chat.tsx implement the requested messages/countdown, clear-on-response, Stop
  cleanup and Retry (resubmit last user question without deleting prior results).
  Native exhausted errors remain expandable. No dependency changes.
- Verified: 45 distinct focused backend context/limit/retry checks pass, including 23 retry
  cases. The combined run passed 44; the subsequent retry run passed 23 with
  one additional native SDK-client wiring check. Eight focused client error/limit
  regressions pass; app TypeScript,
  targeted ESLint, Black/isort, Prettier and whitespace checks pass. SDK mock
  HTTP tests emit four legacy-httpx deprecation warnings; product uses its normal
  SDK HTTP client. These are protocol tests, not live reliability/usage claims.
- Browser countdown/click validation was attempted but is pending: existing
  frontend server on 18000 did not respond, and Next.js refused a second server
  for this checkout. The existing process was preserved. No DB/live OpenRouter
  calls or backend image deployment. All changes remain uncommitted for review.

## Token-limit recovery — approved follow-up

- ask/transport.py handles native SDK UsageLimitExceeded only when measured input,
  output or total usage exceeds its configured token limit. Request/tool limits
  and unrelated/provider errors keep their existing native error path.
- Both planning failures and mid-stream failures emit one token_limit envelope,
  original retrieved results/presentation references, native diagnostic/request
  reference, and a deterministic brief text summary with a narrower follow-up
  suggestion. No extra model call or budget increase. Stream finishes as length.
- ask/contracts.py and frontend contracts.ts align status=token_limit and the
  usage_limit issue. ResultNotices.tsx marks results incomplete and collapses the
  diagnostic. Existing UI fallback adapters/dashboard links and downloads remain
  available without an agent presentation; Python does not select UI adapters.
- Added focused test_limits.py: recorded APOE rows through a minimal FastAPI app,
  real SDK streaming, injected protocol model/planner and real SDK UsageLimits
  checks. Covers planning, input/output exhaustion, already-selected presentation,
  preservation and clean completion, plus unchanged request/unrelated errors.
  These are protocol checks, not live token measurements or scientific validation.
- Added client ask-limits.test.ts to validate the incomplete envelope and native
  diagnostic. The eight targeted client error/limit checks pass; TypeScript,
  ESLint and Prettier pass. Combined backend context/limit checks: 22 passed.
  Command: the focused pytest command below with test_limits.py added alongside
  test_context.py. Black/isort and both repositories' diff checks pass.

Deploy the paired frontend/backend changes together: older strict frontend schemas
reject the new status. Provider-specific context-window errors are not identified
by brittle message parsing and retain their normal diagnostics. Local browser and
real API/OpenRouter validation remains outstanding. Changes remain uncommitted.

## Implemented

- ask/planning.py defines selective GeneEvidence requirements (annotations,
  memberships, xrefs, publications, transcript identities/locations, exons).
  Frontend planning.ts and generated domain enums accept the paired field.
- ask/results.py preserves identity, query parameters, limit, sources and page
  metadata; includes only requested available annotation collections. Explicit
  omissions/unavailable fields distinguish missing evidence from biological
  absence. Transcript projections omit exons unless needed; an exact selected
  transcript is resolved before the existing twenty-item preview cap. Raw rows
  remain unchanged.
- ask/tools.py and operations.py keep brief gene lookup as default, with opt-in
  full content through the existing gene endpoint when annotations are needed.
- ask/context.py folds unambiguous completed exchanges into one server-owned
  run-local snapshot, deduplicating evidence by result ID. It preserves mixed
  assistant text, original conversation, pending/retry calls, tool arguments,
  distinct scopes/pages, diagnostic output and presentation intent. Conflicting
  or unsupported exchanges stay intact. Internal reasoning attached to fully
  completed calls is discarded. Apply only when serialized history is smaller.
- ask/agent.py registers ProcessHistory and explains evidence reuse/grounding.
  Budgets, cross-turn re-fetch policy, v4 results, UI rendering and raw downloads
  are unchanged. There is no cross-turn evidence memory.

## Verification

Focused command (no application startup or database configuration):

```sh
PYTHONPATH=components:bases projects/open-access-api/.venv/bin/python -m pytest --confcutdir=test/bases/niagads/open_access_api/ask test/bases/niagads/open_access_api/ask/test_context.py -q
```

16 passed. Evidence tests use the existing recorded APOE response; protocol cases
and the injected FunctionModel check message bookkeeping, not biological/model
quality. Real SDK streaming completes, retains original retrieved records and
presentation IDs, and emits the v4 envelope. The SDK normalizes adjacent outgoing
requests, so server metadata is checked before normalization and snapshot content
is checked in the model-facing history. Both layers are exercised.

Client tsc --noEmit, targeted ESLint and Prettier checks passed. Black reports
eight files unchanged; isort and both repositories' git diff --check pass. Black
warned that its Python 3.12 runtime is older than the configured Python 3.13
target; the focused tests run successfully on Python 3.12. No repository-wide
suite or browser checks.
Size comparisons are serialized JSON bytes, not provider tokens or measured cost
savings. Compaction cannot recover already-spent cumulative tokens; large requested
annotation collections may still reach existing limits.

## Remaining local step

Review both diffs, deploy/rebuild the backend through the normal local workflow,
and validate representative annotation/structure and multi-tool queries against
the real API and OpenRouter. Record per-call provider usage, planner usage,
grounding and diagnostics. The existing localhost Docker image has no hot reload;
these cloud source changes are not deployed. Cross-turn context/cache remains a
separate deferred task; never trust browser dashboard payloads as evidence.

---

## Historical paused checkpoint

# ASK compact working context checkpoint — paused 2026-10-21

User explicitly requested pausing and resuming when they return. No automatic
resumption is scheduled. No platform usage reset time is known.

## Current task and authorization

- Work in the original niagads-pylib checkout on `refactor/api`; no new branches,
  worktrees or subagents. Original checkout was clean.
- User approved retaining useful annotation evidence in model-facing summaries
  and replacing completed tool exchanges with compact working context. Preserve
  full records server-side, result IDs, query scope, sources, pagination, warnings,
  presentation state, diagnostics and follow-up correctness. Do not raise limits.
- Omit transcript/exon details from model context when not needed, retaining them
  in stored records. Use the existing semantic planner, not keyword heuristics.
- User authorized one live reproduction and focused ASK regression tests earlier
  in this conversation. Load ../.env without displaying values.
- Frontend localhost:3000 has hot reload; backend localhost:8000 is Dockerized
  WITHOUT hot reload. Source changes do not update its running image.
- Existing handoff rejects toy genomic fixtures: use recorded real APOE data for
  evidence tests; message-protocol tests must not establish scientific claims.

## Completed work and changed files

- Added implementation plan/ledger:
  `developer-notes/plans/ask/compact-working-context.md`.
- Added three real-record regression cases:
  `test/bases/niagads/open_access_api/ask/test_context.py`.
  These use the existing recorded APOE API response fixture and verify annotation
  evidence retention and selective structural summaries without mutating records.
- No production code has changed. No Docker restart/rebuild, live reproduction,
  branch creation, commit or frontend changes have occurred.
- ASK_NIAGADS_HANDOFF.md updated with a paused-task pointer.

## Checks run

Command:
`PYTHONPATH=components:bases .venv/bin/python -m pytest test/bases/niagads/open_access_api/ask/test_context.py -q`

Result: 3 expected failures, all because ResultStore.summary does not yet accept
`include_structure`. This is the initial RED step; implementation is pending.
Environment was loaded by test/conftest.py. No processes remain running.

## Findings already established

- Pydantic AI 2.57.0 has ProcessHistory; no ASK history processor exists yet.
  ProcessHistory rewrites ctx.messages before model calls. Preserve provider
  tool-call/return pairing and retries, and verify streaming with the adapter.
- Full rows already stay in ResultStore; OpenRouter receives tool summaries.
  Gene report previews omit useful gene fields and nested annotations. Captured
  model reasoning explicitly sought annotations hidden by those previews.
- get_gene_structure separately adds up to 20 transcript IDs/names/locations.
- Planner and main agent share cumulative input_tokens_limit=20000, request,
  output and deadline budgets. present_results does not end a run.
- Captured APOE run input tokens: 1504, 1154 (planner validation retry), 2548,
  2908, 3590, 4954 = 16658. Another failure reached 28770; the exact original
  20543/request-reference incident is still unlocated. Do not conflate traces.
- Recorded real APOE fixture sizes (JSON characters): structure ~15238,
  memberships ~9216, functional_annotation ~1128. Do not label chars as tokens.

## Exact next step

Resume Task 1 of the saved plan. Implement ResultStore.summary(result_id, *,
include_structure=True): gene identity and useful annotation fields, scope/limit
and source metadata, explicit structure omissions or the existing transcript
preview with requested exon evidence. Add QueryPlan.include_gene_structure with
semantic planner instructions, and route summary selection through _execute.
Move the existing structure summary logic from tools.py into ResultStore.
Then rerun the three regression cases, fixing genuine discrepancies only.

Next implement ProcessHistory in ask/context.py. Fold only complete matching
tool-call/return exchanges into one metadata-marked server-generated JSON snapshot
with tool names/arguments and evidence. Deduplicate by result ID, preserving
distinct pages/content/scopes and presentation intent. Keep pending/retry
exchanges, diagnostics and original user/assistant conversation. Do not identify
snapshots by a spoofable user-text prefix. Add protocol/streaming tests before
production implementation. Register in agent.py and add snapshot grounding/reuse
instructions. Verify authorized focused ASK checks and one live diagnostic using
modified local source against real backend retrieval. Do not confuse the old
Docker image with the modified source. Update handoff and plan with actual results.

---

# Historical ASK answer feedback checkpoint

Implementation added across niagads-pylib and niagads-viz-monorepo:

- Python ASK config, response contract, telemetry availability, streaming context,
  and `/ask/feedback` endpoint; new `ask/feedback.py` signs references and emits
  Logfire feedback events.
- Client response contract, `Feedback.tsx`, Chat integration, styles, and
  `/api/ask/feedback` proxy.
- Added backend feedback tests and client schema/proxy tests, all unrun.
- Replaced the signing-secret ENV setting with `ASK_FEEDBACK_ENABLE`; both API
  runtime ENV samples set TRUE. The signing key is derived automatically from
  the existing Logfire token using a feedback-specific HMAC label, so workers
  using the same token share it without extra configuration or secret files.
  Updated documentation and the unrun backend tests for the explicit flag.

No tests, checks, or final diff review performed, as requested. No credentials,
database, flat-file feedback store, or chat memory added.

Next step: when the user returns, review the implementation diff in both repos.
Then, only with authorization, run focused checks and feedback tests. Verify in
the browser that completed answers show rating controls, either selection opens
the comment form, successful submission shows confirmation and prevents another
submission, failure preserves input for retry, and absent telemetry hides controls.
Verify a submitted event links to the original response trace in Logfire.

User requested deferring review/checks for approximately 1 hour 15 minutes.
No platform usage reset time is known. No automatic resumption is scheduled.
