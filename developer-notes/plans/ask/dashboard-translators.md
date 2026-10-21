# ASK dashboard translators: contract proposal

Status: user approved interfaces and category policy; implementation complete.

## Preparation

- Python branch: codex/ask-dashboard-translators, from refactor/api at ef6d2ba1.
- Frontend branch: codex/ask-dashboard-translators, from app/oa-api at c3962e5f.
- Existing structured-query-planning branches are preserved and not dependencies.
- Read both AGENTS.md files and current handoffs before implementation.

## Proposed interfaces

Keep authoritative ResultSet rows, pagination, provenance and warnings unchanged.
Replace the component-only Presentation selection with a discriminated selection:

```typescript
type Presentation = {
    translator: TableTranslatorId | "category_counts_bar" | "association_counts_bar";
    result_id: string;
    title: string;
    slot: "primary" | "secondary";
    parameters: TableParameters | CategoryCountsParameters | Record<string, never>;
};
type TableParameters = { columns?: string[] };
type CategoryCountsParameters = { group_by: string };
```

The actual schema discriminates parameters by translator, rather than accepting
arbitrary unions. Column IDs and group_by refer only to registered logical fields;
no arbitrary object paths, expressions, callback functions or component props.
Omitted columns use the translator's curated column set. Explicit unknown fields
fail validation. Registered required identifier columns cannot be removed.

Table translator IDs: search_matches_table, gene_records_table,
variant_records_table, track_records_table, associations_table,
association_counts_table. Each registers compatible entity/annotation/content,
field mappings, column types, and supported grouping fields.

The TypeScript translator entry accepts the referenced ResultSet and validated
parameters and returns component props for packages/Table or BarChart, plus scope
and explanatory labels. Use exported TableConfig types rather than a second
table component interface. Validate row shapes before conversion. Preserve raw
records for inspection; unsupported structures remain available there, not as
automatically stringified table columns.

Python validates selection compatibility and parameters against registered
capabilities. ResultStore.summary advertises eligible translator selections and
fields so the agent chooses from actual capabilities. Export the shared vocabulary
and rules through the existing exporter; mirror strict presentation validation
in Zod. Mapping and aggregation execute in TypeScript, never in LLM output.

Changing Presentation is a breaking wire change: propose envelope version 3 with
coordinated Python/client updates. Do not silently reinterpret version-2 payloads.
Existing diagnostics remain intact.

## Data mappings and behavior

- SearchMatch: ID, label, description, matched text, record/match type, rank and
  nullable semantic score. Label score as semantic similarity, not significance.
- Gene/variant/track records: curated explicit fields from existing record models;
  stable IDs, labels, coordinates and relevant categories/booleans. Known nested
  fields have explicit mappings; unrelated nested content stays in raw records.
- Associations: variant, chromosome, position, alleles, reported p-value,
  neg_log10_pvalue, track and explicit trait labels. Preserve reported p-value text
  without underflow or zero substitution; retain the separate numeric significance
  field. Account for the Table package's current numeric p-value accessor when
  selecting its rendering/sorting representation.
- Counts: association_counts_table and association_counts_bar consume the existing
  API summary fields track and num_associations. Do not recompute those counts.
- category_counts_bar counts returned rows by a registered scalar categorical
  field. Do not group by identifiers, free text or semantic scores. Include missing
  values as an explicitly labelled category, without merging a real value of the
  same name. Do not count a list-valued field without a separately agreed unit.
- Keep linked table pie/select/multiselect/boolean filters where appropriate.
  Disable column filtering on all numeric and p-value columns: histogram filters
  are buggy and explicitly excluded. No histogram fixes or numeric coercion to
  categorical values in this task.
- Standalone bars are independent of table filtering. No standalone pie or shared
  cross-panel state. Table pagination describes loaded rows; it is not API paging.
- Tables and bars state their source scope. Loaded-row counts do not imply database
  totals; API aggregate rows are labelled as returned API summaries and retain
  has_more warnings. Semantic candidate sets are never labelled exhaustive.

## Category policy proposed for review

Reuse the existing table filter policy unchanged: seven categories including
Other, with missing values handled by existing controls. For standalone bars,
propose a configurable maximum of seven displayed categories, using that existing
value as the initial setting. When exceeded, keep the table and explain that a
bar is unsuitable; do not silently truncate, invent Other, or change the data.
The user approved this policy; it is implemented through ASK_MAX_BAR_CATEGORIES,
transmitted to the client in the v3 envelope.

## Verification and follow-up

Cover explicit mappings, null/false/zero values, scientific p-value strings,
semantic scores, compatible/incompatible translator selections, categorical
counts, missing categories, excessive cardinality, empty and paginated data,
and disabled numeric filters. Run syntax/type/style checks; execute tests only
on explicit request under repository instructions. No live model or database
calls. No SQL, ORM, ETL, embeddings, retrieval or structured-planning changes.

TODO: repair table histogram filters in a separate task. Next chart extension:
regional Manhattan using genomic position and -log10(p), configurable disease and
population grouping; preserve distinctions between p-values and other measures.

## Progress and rulings

- User approved translator interfaces, envelope v3 and category policy before product changes.
- Registry, typed selection validation and advertised capabilities implemented.
- Mapping rules exported; TypeScript conversion and renderer integration implemented.
- P-value strings retain their reported text. A narrow Table accessor/renderer change
  avoids underflow. Decimal p-values sort without floating-point conversion;
  nondecimal reported strings remain visible with p-value sorting disabled.
- No compatible translator: preserve raw results rather than invent a generic mapping.
- Added/updated focused test cases; did not execute tests under AGENTS.md.
- Python v3 JSON schema generation, app TypeScript/ESLint passed. Table source
  TypeScript passed using --ignoreDeprecations 5.0 to override its existing config
  mismatch with the installed compiler. Repository TypeScript configuration unchanged.
- No live model/database requests, SQL/ORM/ETL/embedding/retrieval changes, worktrees,
  dependency installs or structured-planning changes.
- Independent whole-change review found no high-confidence actionable issues.
- Python AST/Black/isort/diff checks passed. App and Table source TypeScript and
  targeted ESLint passed; final renderer check repeated after a small ID fix.
- Multiple panels for one result receive distinct table/chart IDs using panel index.
- Runtime tests/browser/model/database validation remains unperformed; static
  verification and review do not establish live behavior.

Next step: local integration review after fetching both branches and rebuilding
the workspace Table package. Run tests only on explicit request.

## Follow-up: track selection and fetch

User approved continuing on the same branches. Add optional positive
rowSelectOpts.maxSelectedRows to Table, retaining unlimited selection for existing
callers. ASK track lists set five. At the cap, permit deselection and reject bulk
additions, counting active selections across pages and filters.

Fetch button calls the new Next.js /api/track-data proxy, which requests fixed
/track/{track_id}/data paths in parallel without parameters. The existing endpoint
is in another branch; no backend data route, SQL, ORM or retrieval tool added.
Canonical associations_table now supports track entity; mapping rules regenerated.

Append a separate association table per action. Preserve requested track IDs
separately from returned track fields, per-track raw responses, pagination, empty
successes and failures. No fake combined paging or inferred completeness. The
translator input now explicitly requires only presentation data, allowing local
action results without fabricating an LLM ResultSet envelope or applying its
100-row cap. No model/history round trip or automatic pagination.

Implementation and independent static review complete; no actionable findings.
App/Table TypeScript, targeted app ESLint, Python style and diff checks passed.
Focused cases added but not run under AGENTS.md. Table bundle/declarations built
with a temporary TypeScript compatibility override (existing circular-import and
external-dependency warnings); tracked build configuration unchanged. The first
build attempt failed because Node --input-type propagated to minifier workers;
rerunning from a temporary script resolved it. No live endpoint/model/database
requests.

## Correction: gene-to-phenotype mapping

User reported the unconditional unavailable notice despite returned association
traits supporting phenotype mapping for queried genes. Removed the placeholder
tool rather than adding a new retrieval endpoint. Added deterministic summaries
of context/term/CURIE/source tracks over retained association rows and expose the
original query scope. Both full and API count-summary rows are supported without
recomputing counts. Agent instructions route known-gene phenotype questions to
get_gene_associations and preserve page/source/causality limits. Unseeded inverse
requests require scope clarification; semantic hits are not association evidence.

Added focused cases for terms beyond the scalar preview, context/source dedup,
missing terms/sources, API summary counts and excluding semantic candidates from
trait evidence. Tests were not executed. Python syntax/Black/isort, tool-schema generation and
both repository diff checks passed. Independent targeted static review found no
high-confidence defects. No live model/database calls.

## Development-base merge — 2026-10-21

Merge refactor/api 4fe3a8de and app/oa-api 7d21bf3e into their dashboard branches.
Resolved Python root TODO modify/delete by preserving its removal and moving only
the dashboard follow-ups to developer-notes/TODO.md. Resolved Results.tsx by
retaining translators/grouped results, selection actions and full raw provenance
inside the base's Card/CardHeader/CardBody layout, preserving its Alert rendering.
Aligned the new action proxy/tests/docs with API_INTERNAL_URL and the actual
merged /record/track/{track}/data endpoint. All other incoming changes retained.

Full staged diff checks report existing whitespace in incoming base files,
including unrelated niagads-main source/SVG assets and Python README/TODO prose.
The dashboard changes relative to the incoming bases pass diff checks; unrelated
base whitespace was not rewritten. Tests/live model/database calls remain unrun.

Validation: merged Python AST and ASK response/tool schemas passed; transport
Black/isort passed. Independent merge review found no actionable issues. UI rebuilt
using the existing temporary compiler override; warnings include an inherited
deprecated Card import and unresolved declaration aliases/bundling directives.
No tracked build configuration changed. Frontend type/lint checks recorded below.

Final frontend verification: full open-access-api-client TypeScript and targeted
ESLint (Results, track-data proxy and action cases) passed after the UI rebuild.
All merge conflicts resolved. Tests and live endpoint/model/database checks not
executed. Both development-base merges committed and pushed to dashboard branches.
