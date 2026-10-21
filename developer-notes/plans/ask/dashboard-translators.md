# ASK dashboard translators: contract proposal

Status: awaiting the user-requested interface review before product implementation.

## Preparation

- Python branch: codex/ask-dashboard-translators, from refactor/api at ef6d2ba1.
- Frontend branch: codex/ask-dashboard-translators, from app/oa-api at c3962e5f.
- Existing structured-query-planning branches are preserved and not dependencies.
- Read both AGENTS.md files and current handoffs. No product code changed yet.

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
This policy is proposed, not implemented pending review.

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

Next step: user reviews this contract proposal, then implement mappings,
presentation validation/agent capability metadata, renderer integration and
focused verification; update both handoffs and commit/push the implementation.
