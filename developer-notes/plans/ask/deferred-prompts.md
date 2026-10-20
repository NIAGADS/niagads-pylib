# ASK: deferred design prompts

> **Status: deferred discussion only.** Codex and other agents must treat this
> file as reference material, not active instructions or an implementation plan.
> Do not execute these prompts or change code based on this file unless the user
> explicitly selects a prompt for work. A TODO link does not activate a prompt.

Each numbered prompt stands alone so it can be selected independently. Append
future prompts with a new number; keep existing numbers stable.

## Prompt 001: Review assumptions and extension points

```text
Review the ASK layer for hard-coded entity lists, tool choices, mappings, and
workflows. Treat supplied example requests as representative, not exhaustive.
Explain which restrictions are intentional capability boundaries and which
require developer changes as capabilities grow. Identify existing metadata or
discovery mechanisms that could provide an authoritative source instead of
duplicated lists. Include semantic search's track/gene model mapping and what
must change when OntologyTerm, Variant, or another entity is added.

Present the findings and unresolved design choices for discussion before
implementing changes. Preserve explicit control over which operations ASK may
invoke; discovering an operation does not authorize exposing it as a tool.
```

## Prompt 002: Design handling for unexpected requests

```text
Review how ASK handles requests beyond the supplied examples. Distinguish:

1. Unexpected wording or combinations of supported capabilities: determine how
   the model can compose existing tools without predefined request workflows.
2. A new entity supporting an established operation: identify how existing model
   metadata or a capability registry could avoid hidden, duplicated mappings.
3. A capability or data source that is unavailable: determine when to explain
   the limitation and when to ask a targeted clarification. Do not invent tools,
   data, or successful results.

Inspect the existing implementation before recommending a design. Surface
unresolved boundaries for discussion before implementing changes.
```

## Prompt 003: Evaluate a proposed design beyond its examples

```text
Before implementing a proposed ASK design, walk through several requests that
were not supplied as examples. Include an unfamiliar phrasing, a combination of
supported operations, an ambiguous request, and an unsupported capability.
Also trace the developer changes needed to add a new searchable entity.

For each case, explain the expected tool selection, clarification or limitation,
and any hard-coded assumptions the walkthrough exposes. Present the findings
for design review before implementing changes.
```

## Prompt 004: Phenotype annotation counts and interactive pie chart

```text
Explore an ASK tool and result contract for counts of phenotype annotations,
with a possible pie chart presentation. Consider an interactive version where
the user selects a phenotype and the chart redraws with the corresponding data.

Inspect existing annotation retrieval, aggregation, result contracts, and chart
support before proposing additions. Clarify what is counted, what each slice
represents, the denominator, and whether categories overlap; do not assume
annotation counts and counts of distinct annotated entities are interchangeable.
Determine whether a pie chart fits the data and discuss alternatives if needed.

Consider a result contract carrying category counts, the selected phenotype,
applied filters, and provenance. Identify how the phenotype selector obtains
its choices and how a selection retrieves updated counts and redraws the chart.
Keep database aggregation in the ORM layer and reuse existing API conventions.

Present the proposed tool/contract, interaction, and unresolved choices for
discussion before implementing changes. This is a deferred idea, not an
approved feature specification.
```
