# ASK compact working context implementation plan

> Use superpowers:executing-plans to implement this plan inline.

**Goal:** Reduce repeated model context without losing retrieved annotation
evidence or changing the meaning of the user's question.

**Architecture:** Keep ResultStore authoritative. Enrich its gene summaries and
use Pydantic AI 2.57.0 ProcessHistory to replace completed tool exchanges with
one compact JSON evidence snapshot. Preserve original conversation, unfinished
calls and retries. Use the existing semantic planner to identify requests needing
transcript/exon details; never delete those details from stored records.

**Spec:** Approved design in this conversation: preserve annotation facts, result
IDs, scope, sources, pagination, warnings and presentation state; retain useful
annotations in summaries while full datasets remain server-owned.

## Constraints and review focus

- Work on refactor/api in the original checkout; no branches, worktrees or agents.
- Do not raise budgets, change provider routing, terminate on presentation,
  change API pagination or trust client tool outputs.
- Preserve full stored records and existing follow-up re-fetch behavior.
- Use recorded real gene data and authorized focused tests/live reproduction.
- Do not rebuild/restart the Docker backend without a concrete deployment step;
  distinguish local source verification from the running image.
- Preserve multiple pages/scopes, unknown-tool diagnostics, retry call pairing,
  repeated processor invocation and prior conversation.

## Task 1: Evidence summaries

Files: ask/results.py, ask/tools.py, ask/planning.py; focused ASK context tests.

- [ ] Add tests using the recorded APOE API response: gene identity, functional
  terms and membership evidence survive; stored structure remains unchanged.
- [ ] Run tests and confirm the missing-summary failure.
- [ ] Include gene identity and annotation fields in gene report summaries.
  Include parameters, limit and complete bounded source IDs in every summary.
- [ ] Add QueryPlan.include_gene_structure (default false) with semantic planner
  instructions for transcript/exon/structure requests. Move structure summary
  generation to ResultStore.summary(result_id, *, include_structure=True).
  Omissions and the existing 20-transcript preview cap remain explicit.
- [ ] Verify with focused tests and formatting checks.

## Task 2: Working context

Files: ask/context.py, ask/agent.py; focused ASK context tests.

Interface: compact_history(ctx: RunContext[dict], messages: list[ModelMessage])
returns list[ModelMessage], registered through ProcessHistory.

- [ ] Add protocol tests for completed pairs, multiple pages/scopes, diagnostics,
  retries, original conversation, idempotence and request isolation.
- [ ] Confirm failure before implementation.
- [ ] Fold only complete matching tool-call/return exchanges into JSON outcomes.
  Deduplicate successful retrievals by result ID and presentations by intent;
  retain tool names/arguments and non-dataset outputs. Keep pending/retry
  exchanges intact. Mark the server-generated snapshot using message metadata,
  never a user-supplied text marker. Serialize JSON without whitespace padding.
- [ ] Register the processor and explain snapshot grounding and result reuse in
  agent instructions. Advise against fetching unrelated structure and repeating
  completed retrievals; presentation still does not end the run.
- [ ] Verify real-data streaming with an injected FunctionModel and compare
  request sizes with/without compaction using the same recorded exchanges.

## Task 3: Verification and handoff

- [ ] Run focused ASK regression tests (environment loaded by test/conftest.py),
  Black/isort checks and git diff --check. No repository-wide tests.
- [ ] Run one authorized live APOE diagnostic with modified source, real backend
  retrieval and configured OpenRouter model; record per-call provider usage and
  input component sizes. Do not treat characters as token counts.
- [ ] Review diff and update ASK_NIAGADS_HANDOFF.md with changes, evidence,
  commands/results, limitations and backend rebuild instructions.

## Execution notes

- Initial checkout clean on refactor/api.
- User explicitly requested plan and immediate execution; no extra approval gate.
- Existing handoff rejects toy genomic fixtures. Use the recorded real APOE data
  for evidence tests; message-protocol tests are separate from scientific claims.
- Keep changes uncommitted for user review. Self-review only under the user's
  no-subagents instruction.
