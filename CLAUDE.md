# Repository navigation

Read `AGENTS.md` for the repository's working rules before making changes.
This file supplements those rules with a map of the source tree and search
guidance. Run the commands below from the `niagads-pylib` repository root.

## Polylith layout and Python imports

This is a Poetry-managed Python monorepo using Polylith's `loose` structure
and the `niagads` namespace (see `workspace.toml`). Source code is split across
`bases/niagads/` and `components/niagads/`. There is no root `niagads/` or
`src/niagads/` source directory.

| Location | Contents |
| --- | --- |
| `bases/niagads/` | Application entry points, service routes, tools, and concrete ETL plugins. |
| `components/niagads/` | Reusable domain models, database code, API services, and utilities. |
| `projects/` | Deployable project definitions, dependencies, packaging, and deployment configuration. Most Python application code lives in the shared bases and components. |
| `test/bases/niagads/` | Tests organized by base name. The directory is `test`, singular. |
| `test/components/niagads/` | Tests organized by component name. |
| `development/` | Experiments, exploratory scripts, sample data, and manual investigations. |
| `developer-notes/` | Design notes, plans, patches, and task-specific reference material. |
| `docs/` | Deprecated Sphinx documentation; ignore unless explicitly requested. |
| `.agents/skills/` | Repository-specific agent skills. |

Map imports to source paths by checking both source roots:

| Python import | Source file |
| --- | --- |
| `niagads.open_access_api.app` | `bases/niagads/open_access_api/app.py` |
| `niagads.api.common.services.query` | `components/niagads/api/common/services/query.py` |
| `niagads.database.genomicsdb.schema.gene.documents` | `components/niagads/database/genomicsdb/schema/gene/documents.py` |
| `niagads.common.models.base` | `components/niagads/common/models/base.py` |

An import may also resolve to a package's `__init__.py` or a symbol re-exported
there. Do not assume the import's last segment is a filename.

Each `projects/<name>/pyproject.toml` identifies that project's included bricks
through `[tool.polylith.bricks]` and `[tool.poetry].packages`. Paths such as
`../../components` are relative to that project directory. Project directory
names can use hyphens while Python package names use underscores; for example,
`projects/open-access-api/` packages `bases/niagads/open_access_api/`.

## Where to look first

| Task | Starting location |
| --- | --- |
| Open Access API application and routes | `bases/niagads/open_access_api/app.py`, `bases/niagads/open_access_api/routes/` |
| ASK NIAGADS agent, tools, streaming, result contracts | `bases/niagads/open_access_api/ask/` |
| Shared API request handling, parameters, response models | `components/niagads/api/common/` (`services/`, `parameters/`, `models/`, `app/`) |
| Query embedding generation | `components/niagads/api/common/services/embeddings.py` |
| ORM models and database retrieval | `components/niagads/database/genomicsdb/schema/` (`gene/`, `variant/`, `dataset/`, `reference/`, `results/`, `ragdoc/`, `admin/`) |
| Database migrations and schema deployment | `projects/genomicsdb-schema-manager/` (`alembic/versions/`, `sql/`, `scripts/`, `initialize-db/`) |
| Concrete GenomicsDB ETL plugins | `bases/niagads/genomicsdb_etl/plugins/` (`gene/`, `variant/`, `dataset/`, `reference/`, `generic_loaders/`, `common/`) |
| Shared ETL pipeline and plugin infrastructure | `components/niagads/etl/` |
| Domain models for genes, variants, tracks, genomic features, search | `components/niagads/common/` |
| Component base mixin and serialized model base | `components/niagads/common/core.py`, `components/niagads/common/models/base.py` |
| Settings and HTTP session management | `components/niagads/settings/`, `components/niagads/requests/` |
| General utilities | `components/niagads/utils/` |
| Packaging and API container configuration | `projects/open-access-api/` |

Other bases include `pipeline_service`, `sql_runner`, and
`metadata_validator_tool`. Other projects include `genomicsdb-loader`,
`metadata-builder`, `niagads-metadata-validator`, `variant-annotator`, and
`examples`. Verify names on disk rather than guessing from an older document.
In particular, the current ETL base is `genomicsdb_etl`, not
`genomicsdb_service`.

## Search and indexing guidance

Use explicit filesystem searches when an index or symbol lookup returns no
results. An empty indexed result does not establish that code is missing.
Start with the relevant subtree and broaden only as needed:

```bash
# Locate filenames without scanning file contents.
rg --files bases/niagads components/niagads -g '*embedding*.py'

# Find a symbol's definition and usages across both source roots.
rg -n 'class QueryEndpointService|QueryEndpointService\(' bases/niagads components/niagads

# Locate related tests, which need not have the same filename as the source.
rg --files test -g '*query*' -g '*embedding*'

# Discover project definitions independently of shared Python source.
rg --files projects -g pyproject.toml

# Discover agent instructions in hidden configuration directories.
rg --files --hidden .agents .codex -g '*.md'
```

`rg` normally respects ignore files and skips hidden directories. If a specific
expected file is absent, inspect its parent directory and applicable ignore
rules (`git check-ignore -v <path>`). Use a targeted `rg --files --hidden` or
`rg --files --no-ignore <specific-directory>` when needed; avoid an unrestricted
repository-wide search through ignored content.

Keep source searches out of `.git/`, `.venv/`, nested project virtual
environments, `__pycache__/`, caches, and `dist/`. Wheels and source archives
under project `dist/` directories are build artifacts, even where tracked;
edit the corresponding base or component instead. Inspect these artifacts only
when the task concerns packaging. Do not scan environment or credential files
for general indexing or display their values.

Refactor branches intentionally contain incomplete migrations and legacy code.
Follow the implementation relevant to the task; a stale path in notes or an
unrelated broken import is not authorization to repair other modules. Consult
`TODO.md`, `ASK_NIAGADS_HANDOFF.md`, or relevant developer notes when the task
calls for their context. Run tests only when explicitly requested, as required
by `AGENTS.md`.
