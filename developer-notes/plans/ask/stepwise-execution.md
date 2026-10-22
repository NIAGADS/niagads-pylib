# ASK incremental dependent execution

User-authorized implementation on codex/ask-stepwise-execution, from updated
refactor/api and app/oa-api. No subagents or live services.

## Design

Retain the existing small interpretation call and PydanticAI evidence-agent loop;
do not introduce an executor. Replace recursive Boolean planning with a bounded
QueryPlan: a short goal, flat concepts, concise constraints, unresolved scope,
necessary clarifications and selective gene evidence. The original request remains
authoritative; interpretation is not a capability check or execution gate.
Preserve compound Boolean meaning in constraints rather than expanding a tree.

Each native tool return determines the next action. Gene and structure tools can
select evidence per call, so dependencies discovered after interpretation are not
limited by its initial evidence fields. A clarification tool records the existing
clarification outcome without inventing missing inputs. Existing unsupported
capability tools retain their native outcomes; instructions require reporting the
limitation and stopping that dependent path while preserving retrieved results.

Keep the data envelope, routes, frontend adapters, filters, deadlines, retry
handling and usage limits. Keep the existing 2,000-token output limit on both
calls; bound interpretation through its flat schema and field/count limits,
without provider-budget tuning. The existing data-niagads-plan event carries
interpretation (not a promised workflow), including in feedback.

## Tasks

- [x] Bound Python interpretation and align frontend validation and vocabulary.
- [x] Instruct the native loop to act incrementally, clarify only material unresolved
      ambiguities, report unsupported capabilities, and retain brief final responses.
- [x] Allow per-call evidence selection and record clarification outcomes.
- [x] Add focused protocol regressions for evidence-dependent calls, clarification,
      unsupported capabilities, and request/tool/deadline bounds. Use existing real
      recorded gene evidence where records are needed, not invented biology.
- [x] Static validation and handoff. AGENTS.md permits tests only on explicit request;
      backend tests are added but not executed. Frontend rules permit running its
      three new contract regressions; all pass. No live provider/database calls.

## Deferred

Pagination remains in developer-notes/TODO.md; no additional-page execution or
paging commentary. OpenRouter/Logfire incident diagnosis remains deferred.
