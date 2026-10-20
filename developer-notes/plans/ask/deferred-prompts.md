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

## Prompt 005: Assess and refactor Polylith boundaries

```text
Assess the ASK NIAGADS implementation for code that belongs in reusable Polylith
components rather than bases/niagads/open_access_api/ask, then refactor the agreed
boundaries. This prompt authorizes assessment first; discuss significant moves
and their consequences before implementing them.

Read AGENTS.md and ASK_NIAGADS_HANDOFF.md in niagads-pylib and the paired
niagads-viz-monorepo. Preserve existing local changes and the current task
branches. Inspect current code and manifests rather than relying solely on the
handoff. Do not launch subagents.

Start with a read-only inventory of ASK responsibilities and dependencies:
agent construction, tools, HTTP retrieval, operation metadata, settings,
result/presentation contracts, result storage and previews, telemetry, type
export, and FastAPI transport. Trace their callers and runtime ownership.

Inspect existing components and nearby bases before proposing destinations.
Reuse applicable utilities, models, mixins, settings, and service patterns.
Classify each responsibility by its actual coupling: reusable application
behavior, shared domain/API functionality, or application-specific entrypoint
and wiring. Identify what should remain in the base as well as what should move.
Do not assume every ASK module belongs in a component, create one large component
solely to relocate the directory, or duplicate existing domain record models.

Present a concrete source-to-destination mapping with the reason for each move,
the resulting brick dependencies, and affected public imports. Explain how
application-specific tools, capabilities, and configuration reach reusable code
without creating component-to-base imports or circular dependencies. Identify
unresolved choices and obtain agreement on the proposed boundaries before edits.

After review, implement the agreed refactor in coherent steps. Preserve API
routes, agent capabilities, model assignments, request limits, settings behavior,
streaming, serialized contracts, and frontend behavior. Keep database retrieval
in the ORM layer. Do not combine relocation with deferred feature work or
behavioral redesign. Avoid redundant wrappers and speculative abstractions.

Update imports, application wiring, Polylith brick/package mappings, dependency
declarations, affected test imports, type-export commands, and developer guides
as needed. Keep optional ASK dependencies consistent with the existing Poetry
setup. Coordinate frontend changes only where the agreed refactor requires them.

Review the final dependency direction and diff. Run appropriate non-test checks;
run tests only when explicitly requested. Do not access the database or make
live OpenRouter calls without separate authorization. Before any OpenRouter
batch, obtain approval for its purpose and maximum request count, including
retries, and track attempts and outcomes.

Report the final responsibility mapping, changed files and import paths,
checks performed, and remaining validation. Do not claim behavior is verified
by file moves or import checks alone.
```

## Prompt 006: Ontology-based retrieval for gene documents and tracks

```text
Implement ontology-based retrieval for gene documents and tracks in niagads-pylib.

Follow AGENTS.md and applicable project skills. Inspect existing retrieval
utilities, models, and mixins before implementing. Do not run tests unless
explicitly requested.

Add a shared OntologyTermRetrievalMixin with a batch method such as
find_by_ontology_terms(session, ontology_term_ids). Keep entity-specific
association queries in the Gene document and Track ORMs. Keep this separate
from SearchMixin: it resolves already identified ontology terms to associated
records.

Support these association paths:

Gene documents:
- GeneModel.gene_type_id -> Gene document through gene_id.
- GOAssociation.go_term_id -> Gene document through gene_id.
- GeneXRef.ontology_term_id -> Gene document through gene_id.

Tracks:
- Track.track_type_id.
- TrackConcept.ontology_term_id -> Track through track_id.
- TrackContext.ontology_term_id -> Track through track_id, covering BIOSAMPLE,
  PHENOTYPE, and EXPERIMENT contexts.

Accept multiple internal ontology_term_id values and perform batch queries
rather than one query per term. Reuse existing return models and retrieval
conventions where suitable. Preserve the mapping between matched terms and
retrieved records, deduplicating repeated associations.

Limit this task to the ORM retrieval capability. Do not change endpoints,
ontology search, ranking, or ontology hierarchy expansion. Other ontology
foreign keys—evidence codes, external database types, and variant traits—are
outside scope.

Review the final diff and run focused non-test checks. Report changed files,
verification results, and any unresolved design questions.
```
