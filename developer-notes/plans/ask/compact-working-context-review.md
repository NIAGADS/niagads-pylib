# Approved revision: ASK working-context compaction

Assessment of compact-working-context.md against refactor/api 494b5800 and
app/oa-api 786f8bb8. The user approved this revision and implementation.
The assessment below records the starting behavior; execution results are in
CHECKPOINT.md. This revision supersedes the original boolean structure toggle.

## Baseline behavior that changed the plan

- Every POST /ask creates a new ResultStore and RunUsage. Planner and evidence
  agent share a cumulative 20,000-input-token budget within that request.
  Compaction cannot recover tokens already consumed or pool budgets across turns.
- Only the last twelve user/assistant text messages are submitted. Client result
  parts are excluded by the frontend and stripped again by backend sanitization.
- The root client session retains chat, dashboard records and fetched track data
  across navigation. This is display state, not trusted server model memory.
- Gene/variant/track report tools now request existing API summary models.
  Full gene annotations in the recorded APOE fixture are not fields guaranteed by
  the production brief lookup. The full-record UI link is a separate fetch and
  does not add evidence to ResultStore or model context.
- The evidence agent already receives bounded tool summaries, not complete rows.
  Enriching every summary with all memberships/publications can increase context.
- There is still no ProcessHistory capability registered on the ASK agent.

## Recommended scope

Implement run-local working-context compaction first. Keep cross-turn semantic
memory/result caching as a separately designed follow-up. Do not trust browser
dashboard payloads, reuse old result IDs in a new ResultStore, or raise budgets.

Keep summary Cards and brief default lookups. Explicit annotation questions may
retrieve full gene evidence using existing API content selection. Full retrieval for reasoning must not imply full record dumps in chat.
Compaction itself cannot supply fields that were never retrieved.

## Revised implementation stages

### 1. Establish a current baseline and retrieval contract

Use existing real APOE records and actual captured exchanges to distinguish:
default brief lookup, annotation questions, structural questions, and multi-tool
discovery. Measure per-call provider tokens where available; serialized character
sizes are separate measurements. Include the planner's share of the run budget.

Preserve gene identity, scope, limits, source IDs, pagination and warnings in tool
summaries. Add only requested evidence, with source attribution and explicit
omissions/counts; do not copy every nested annotation collection by default.

Replace an all-or-nothing structural inclusion policy with semantic evidence needs:
transcript identity/location, exon detail, and general gene annotations are
different requirements. A transcript request must not automatically include all
exons for twenty transcripts. Preserve selected transcript IDs and explain caps;
never omit an explicitly selected transcript merely because it falls after a
preview cutoff. Do not add keyword matching or mutate stored records.

### 2. Compact completed exchanges conservatively

Use the installed ProcessHistory capability. Maintain one server-generated,
run-scoped snapshot; server-owned result IDs resolve to authoritative summaries.
Deduplicate evidence by result ID without merging distinct pages, query scope,
content modes or conflicting outcomes. Preserve tool names/arguments, non-dataset
outputs, presentation intent, warnings and native diagnostics.

Keep pending calls and retries intact, including provider call/return pairing.
Preserve user/assistant conversation. Define handling of mixed text/tool/reasoning
messages explicitly rather than deleting entire messages indiscriminately.
Recognize internal snapshots through request-scoped server metadata/state, never
a user-text prefix. Repeated processing must be idempotent and request-isolated.

Measure compacted versus original histories for the same real exchanges. Do not
assume that inserting a snapshot after one short call saves context. Avoid keeping
both a snapshot and duplicate original evidence. Never silently drop necessary
evidence to make a token check pass. Presentation does not terminate the run.

### 3. Align contracts and verify the actual boundaries

If QueryPlan gains evidence-selection fields, update the strict frontend plan
schema in the same change. Keep dashboard v4, brief chat, raw downloads, record
Cards and error/feedback behavior intact. No UI adapter rules move to Python.

Separate evidence tests using existing recorded real data from generic protocol
tests; neither establishes live interpretation quality. Cover current summary
records as well as full evidence when explicitly retrieved. Cover pending calls,
retries, mixed responses, repeated processing, distinct pages/scopes, failed
retrievals, malformed/foreign snapshots and streaming completion.

Pure context tests should not import the API application or require database
configuration. The attempted focused run in this cloud stopped at conftest import
because DATABASE_URI and CACHE_DB_URI are unavailable; it did not reproduce the
local checkpoint's three RED failures. Isolate fixture loading from app startup
without inventing records or dummy database services.

Live OpenRouter/database validation remains on the user's local system. The old
localhost:8000 Docker image is not this cloud checkout, and source changes must
not be described as deployed. Record actual before/after usage and grounding, not
just successful completion or fewer serialized characters.

## Deferred follow-up

Cross-turn context would need server-owned session/result references, lifetime and
invalidation rules, and explicit evidence freshness/retrieval behavior. Valkey and
user-session infrastructure can support that later. A browser dashboard ID alone
is insufficient. Keep this outside the first compaction change.

## Execution policy revision

Implementation continues in /workspace on refactor/api and app/oa-api, following
the resumed task checkpoint: no new branches/worktrees/subagents; leave changes
uncommitted for review. No database/model requests or backend rebuilds in cloud.
