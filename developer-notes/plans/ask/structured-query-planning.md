# Structured query planning implementation plan

Use Superpowers executing-plans inline. Repository instructions override skill
defaults: subagents require an explicit request; no worktrees requested, no tests or live requests without
an explicit request. The user approved implementing the preceding brainstorming.

## Goal and design

Interpret each ASK conversation into a validated QueryPlan before tool selection,
using the configured ASK_MODEL. Preserve positive concepts and AND/OR grouping,
intent, entity, raw gene/span/variant location, optional flank/assembly,
clarifications and deferred exclusions. Do not invent ontology IDs, coordinates,
participants, missing distances or assemblies. The plan is interpretation, not
retrieved evidence. No additional model/provider setting is introduced.

Planning belongs in ASK; direct /query endpoints remain semantic primitives.
The user explicitly confirmed ASK chat planning; direct query requests are
unchanged.
Do not implement rank fusion, ontology retrieval, exclusions, SQL, ORM changes,
ETL work, or genomic data endpoints. Preserve current error diagnostics.

## Tasks and interfaces

1. Create ask/planning.py: CustomBaseModel contracts, project enum subclasses,
   typed PydanticAI planner, and dynamic instructions for the executing agent.
   QueryPlan has intent, entity, selection (recursive Boolean group or concept),
   location, clarifications and exclusions. Empty groups/terms and negative flanks
   fail validation; unspecified location values remain null. Add focused tests
   for all four representative requests, Boolean grouping, deferred exclusions,
   missing values, invalid output and structured FunctionModel execution.
2. Integrate the planner into transport.py with the existing configured model,
   sanitized text history, deadline, shared RunUsage and UsageLimits. Stream a
   separate data-niagads-plan part, leaving the result envelope unchanged. Pass
   the plan to agent instructions. Stop retrieval when clarification or deferred
   exclusions are present. Add a track-data placeholder tool that reports pending
   retrieval without making HTTP requests. Preserve native error propagation.
3. Export planning enums through the existing type exporter. Add a mirrored Zod
   plan schema and a plain JSON disclosure in the client. Treat the plan as
   interpretation, never data or executable tool arguments. Keep browser history
   text-only; the server regenerates plans. Add frontend schema test cases.
4. Review the whole diff, run allowed syntax/style/type checks, update both
   handoffs with branches, scope and remaining verification, and commit/push the
   scoped branches. No live model/database request is authorized by this plan.

## Review focus

- Greetings/API help do not fabricate search concepts or locations.
- Korean OR Japanese AND PSP preserves grouping and ambiguity.
- Cancer exclusions remain explicit and cannot be claimed as applied.
- Genomic data requests retain loc/flank without inventing available endpoints.
- Planner failures retain diagnostics and cannot fall back to unplanned retrieval.
- Both LLM stages share existing model/token/deadline budgets, including retries.
- Existing caps/defaults and error handling are not redesigned by this task.

## Progress

- Bases reviewed: Python 221082c4 (refactor/api), frontend c3962e5f (app/oa-api).
- New branches: codex/ask-structured-query-planning in both repositories.
- Checkpoints reviewed before implementation. Existing work preserved.
- Test execution deferred under AGENTS.md; add test cases without claiming they ran.
- Contracts, typed planning stage, shared budgets and separate stream part complete.
- Main-agent plan context, clarification/exclusion guards and track-data placeholder complete.
- Generated frontend enums, mirrored recursive schema and plain JSON disclosure complete.
- Focused cases added for the four examples, Boolean grouping, invalid output,
  retrieval guards, unavailable data retrieval and shared request budgets.
- Verification: Python schema generation, AST syntax, Black/isort, full frontend
  TypeScript and targeted ESLint passed. No tests/live requests executed.
- Final review: inline self-review; subagents were not explicitly requested, as required by AGENTS.md.
- Static checks initially found an unknown-to-Error type mismatch and JSX inside
  try/catch in the new view. Validation was separated from rendering and the
  existing error formatter now receives only Error instances; checks then passed.
- Ruling: keep /query primitives unchanged — the user explicitly confirmed
  ASK-only planning, preserving direct retrieval semantics and costs.
- Ruling: no worktrees or test execution; no subagents explicitly requested —
  prior workspace preference and repository rules override skill defaults. Runtime behavior remains unverified.
