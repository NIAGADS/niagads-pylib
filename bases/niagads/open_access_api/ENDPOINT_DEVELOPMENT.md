# Writing Open Access API endpoints

Read the repository's `AGENTS.md` before making changes. Follow the existing
routes and endpoint services, reusing their parameters, validation, response
models, caching, and exception handling. Database retrieval belongs in the ORM
layer, not in a route or ASK tool.

## Define and register the route

Place routes in the appropriate module under `routes/`. Register a new router
through the existing application factory in `app.py` when needed. Give each
operation a unique `operation_id`, a useful description, and response models
that describe the records actually returned.

Use the existing `ResponseConfiguration` distinction between the response
container and its record model. For example, `response_model=RecordResponse`
and `record_model=Gene` represent the response shape `RecordResponse[Gene]`.
Preserve the endpoint's content, format, and pagination conventions. Mark planned
operations with `openapi_extra={"x-status": "planned"}` and return an explicit
not-implemented response until retrieval exists.

See [developer notes](DEVELOPERS_NOTES.md) for shared runtime dependencies,
including the interval-bin reference.

## Register retrieval operations with ASK NIAGADS

**Adding a FastAPI route does not register it as an ASK retrieval operation.**
When adding a retrieval endpoint for ASK, also add its definition to `OPERATIONS`
in [ask/operations.py](ask/operations.py). This is currently maintained manually.
OpenAPI discovery for API help does not make an endpoint callable by the agent.

Each `AskOperation` declares:

- `endpoint`: the existing route path, including any identifier placeholder.
- `entity`: a member of `niagads.common.types.Entity` identifying the query subject.
- `annotation`: a member of `niagads.api.common.types.AnnotationKind`, such as
  `REPORT`, `ASSOCIATIONS`, or `STRUCTURE`. Use `None` for search candidates.
- `response_config`: the existing `ResponseConfiguration`, with separate
  `response_model` and `record_model` classes matching the requested response.

For example, the existing gene-report operation is registered as:

```python
"gene": AskOperation(
    endpoint="/record/gene/{gene}",
    entity=Entity.GENE,
    annotation=AnnotationKind.REPORT,
    response_config=ResponseConfiguration(
        response_model=RecordResponse,
        record_model=Gene,
    ),
),
```

These classes are imported in `ask/operations.py`; reuse the route's existing
record models rather than creating ASK-specific copies. The configuration
describes the route's response; it does not replace the route's validation.
A record is the API's representation of retrieved information. A report is an
annotation kind, not another entity or a presentation component.

Check the operation against [ask/api_client.py](ask/api_client.py). The current
adapter supports GET operations returning a list of record dictionaries under
`data`. It substitutes an identifier placeholder named after `entity.value`,
such as `{gene}`, and forwards other supplied parameters as query parameters.
A different envelope or path structure requires a deliberate adapter change;
declaring different model metadata alone does not add that support.

For a new agent capability, add or update the typed tool in
[ask/tools.py](ask/tools.py) and register it in `build_agent` in
[ask/agent.py](ask/agent.py). Registry entries do not automatically create tools.
Semantic search selection is derived from registered operations whose record
model is `SearchMatch`; it currently selects one search operation per entity.
Adding an entity or annotation enum member alone does not implement retrieval.

## Keep the client contract consistent

ASK results identify `entity` and `annotation` separately. Reuse existing enum
members where they fit. If a new annotation kind is needed, extend
`AnnotationKind` rather than adding independent string lists to ASK or the client.

Tables can display new annotations through the existing adapter. Add an
entity/annotation pair to `SOURCE_CHART_TYPES` in `ask/contracts.py` only when
the records provide the evidence required by the source chart. New presentation
components need their own backend validation and frontend registry entry.

After changing these enums or chart compatibility rules, regenerate the frontend
constants from the Python repository root using its configured interpreter:

```bash
PYTHONPATH=components:bases python -m niagads.open_access_api.ask.export_types \
  ../niagads-viz-monorepo/apps/open-access-api-client/app/ask/types.generated.ts
```

Adjust the destination for your frontend checkout. Commit the generated file
with the corresponding Python change; do not edit it manually. Coordinate
changes to the result envelope with the frontend runtime schema in
`apps/open-access-api-client/app/ask/contracts.ts`.

## Review and validation

Update focused coverage for the route, operation mapping, tool parameters, and
affected result/presentation contracts. Include planned and failed retrieval
where applicable; neither should appear as an empty successful result.

Run tests only when explicitly requested, as required by `AGENTS.md`. Live
OpenRouter calls require separate approval with a maximum request count; track
attempts, including failures and retries. See [ASK_NIAGADS.md](ASK_NIAGADS.md) for
the setup, response contract, and current integration-validation limits.
