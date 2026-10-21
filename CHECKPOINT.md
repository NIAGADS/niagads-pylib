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
