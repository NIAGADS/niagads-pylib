# Open Access API Refactor: Settled Model

## Top-Level API Families

### Root API

- `/status`
- `/openapi.yaml`
- `/openapi.json`
- `/docs`
- `/redoc`
- `/search/...` for aggregate structured retrieval
- `/query/...` for aggregate natural-language / approximate retrieval

### Child Service APIs

- `/status`
- `/openapi.yaml`
- `/openapi.json`
- `/docs`
- `/redoc`
- `/record/...`
- `/search/...`
- `/query/...`
- `/service/...`
- `/reference/...`

## Endpoint Semantics

- `record` = canonical resource retrieval
- `search` = structured retrieval
- `query` = natural-language / approximate retrieval
- `service` = helper / utility endpoints only
- `reference` = reference endpoints such as filter field/value listings

## Canonical Resource Pattern

- `record/<entity>/{id}`
- `record/<entity>/{id}/{subresource}`

Examples:

- `record/gene/{gene}`
- `record/gene/{gene}/pathways`
- `record/gene/{gene}/function`
- `record/gene/{gene}/associations`
- `record/track/{track}`
- `record/track/{track}/data`

## Track Model

- track metadata = track record
- track data = track subresource

Structured retrieval:

- `search/tracks`
- `search/tracks/data`

Natural-language / approximate retrieval:

- `query/tracks`
- `query/tracks/data`

FILER and GenomicsDB should converge on this model.

## Representations

- Paths identify the resource or operation.
- `format`, `content`, and `view` remain representation parameters.
- No representation-only routes such as `/summary`, `/counts`, `/ids`, `/urls`, `/table`, or `/browser`.
- Valid `format`, `content`, and `view` values are endpoint-specific.

Examples:

- `record/track/{track}?content=summary`
- `record/track/{track}?view=table`
- `search/tracks?content=ids`
- `search/tracks/data?content=counts`
- `query/tracks?view=table`

## Reference Endpoints

Use `reference`, not `dictionary`.

Initial candidates:

- `reference/filters`
- `reference/filters/{field}`

## Notes

- Root owns cross-service aggregation for `search` and `query`
- Child services own canonical `record` endpoints
- Search/query behavior should not live under `service`
- Abandoned FILER QTL beta endpoint is out of scope and should be removed
