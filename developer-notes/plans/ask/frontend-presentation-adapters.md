# Frontend-owned ASK presentation adapters

User-approved boundary: UI handles UI. Continue on codex/ask-dashboard-translators
in both repositories; query planning is independent and remains untouched.

## Design and tasks

1. Python owns authoritative ResultSet data/provenance/query/pagination and coarse
   PresentationIntent only: result_id, view (auto/table/plot), title, optional
   plot_type/group_by/x/y hints. Plot types/field hints are open strings, not a UI
   adapter/component registry. Validate result references and intent structure,
   never columns, component props, chart eligibility or rendering configuration.
   Preserve phenotype summaries and existing retrieval/model/error behavior.
2. Remove ask/presentations.py, capability advertising and exported table rules.
   Export data enums only. Remove server max_bar_categories and automatic server
   table choices. Breaking wire change: envelope version 4, coordinated client.
3. Frontend owns adapters for expected API outputs, local field mappings and row
   validation. Retain typed tables, categorical filters, scientific p-values,
   track selection/fetch, independent category/aggregate bars, raw/provenance,
   paging and partial failures. Default auto to an appropriate table. Explicit
   table requests stay tables; explicit plots use local adapters or show an
   explanatory notice. Unsupported plot types/axes/groupings never silently
   become another plot/table. Retain data inspection. No new chart families.
4. Bar category limit moves to NEXT_PUBLIC_ASK_MAX_BAR_CATEGORIES, default 7,
   positive integer. UI owns this policy; existing histogram exclusion stays.
   Add/update focused contract/adapter regression cases. Tests remain unrun under
   AGENTS.md unless explicitly requested; run syntax/schema/style/type checks.
   Review whole change, update handoffs, commit/push both existing branches.

## Interface reasoning

Keep stable domain data enums shared; component/adapter names remain TypeScript.
Use local adapters for SearchMatch, gene/variant/track records, association rows
and API aggregate counts, following Charts translator ownership. Source schema
changes can require adapter updates; changing columns/filters/components cannot
require Python changes. UI validates hints against data it can actually render.
Missing data/unknown outputs remain inspectable with an explanation.

## Verification focus

- Python accepts a new plot name without code changes; rejects executable props
  and forged result references. No UI registry/config remains in Python.
- Changing frontend mappings requires no regeneration of Python exports.
- Explicit table/plot intent is honored; unsupported plotting is explained.
- Null/false/zero, p-value strings, source/query/page metadata are preserved.
- Track action results use the same local adapters without LLM calls.
- No SQL/ORM/ETL, endpoints, embeddings, model config or query planning changes.

## Progress

- Checkpoints/current branches reviewed; working trees clean at start.
- User explicitly approved implementation after discussing the responsibility split.
- Existing checkouts/branches retained; no new worktrees or installs needed.
- Execution inline; repository test restrictions override test-running skill steps.

- Python intent contract, ownership validation, agent instructions and enum-only
  exporter implemented; server UI registry/config/capability fallback removed.
- Local expected-record adapters and view resolver implemented. Auto defaults to
  table unless plot hints are supplied; explicit table takes precedence. Plot hints
  support known native API paths through registered UI field mappings; unknown
  plots/axes/groupings produce a notice and retain raw records.
- Existing track action uses the same local table adapter without an LLM roundtrip.
- Focused cases added/updated for generic intent, future plot names, field aliases,
  explicit table/plot choices, unsupported plots and preserved data/paging.
- Python AST/Black checks and v4 response/tool schema generation passed.
- Final frontend TypeScript and targeted ESLint passed after the review fix.
- Python isort, generated response/tool schemas and both git diff --check passed.
- Documentation updated; previous v3 plan/handoffs explicitly superseded.
- No tests/live model/database calls or unrelated shared-component changes.

## Review

Independent whole-change review found one axis-orientation defect: the existing
shared BarChart is horizontal, while the initial adapter accepted reversed
explicit x/y preferences. Added a regression case and now explain unsupported
axes rather than swapping them. Horizontal explicit axes remain supported. No
other high-confidence findings. Regression cases were not executed under AGENTS.md.
No new chart orientation/component API added as part of this ownership refactor.
