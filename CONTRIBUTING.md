# Contributing to NIAGADS Open Access Service

Internal development guidance for `open-access-service`, the NIAGADS Python monorepo. This repository uses the [Polylith architecture](https://polylith.gitbook.io/polylith) and the [Python Polylith toolkit](https://davidvujic.github.io/python-polylith-docs/).

## Requirements

- Python 3.12+ (the original project requirement is `>3.12, <4.0`; consult the root `pyproject.toml` for the authoritative constraint)
- [pipx](https://github.com/pypa/pipx)
- [Poetry](https://python-poetry.org/), installed through pipx
- [Python Polylith tools](https://davidvujic.github.io/python-polylith-docs/), installed as Poetry plugins
- [toml-sort](https://pypi.org/project/toml-sort/), installed through pipx

## Environment Setup

Install pipx and Poetry using their linked documentation. Add the Polylith plugins to Poetry:

```bash
poetry self add poetry-multiproject-plugin
poetry self add poetry-polylith-plugin
```

Clone the renamed repository and install dependencies from its root:

```bash
git clone https://github.com/NIAGADS/open-access-service.git
cd open-access-service
poetry install
```

If working on a specific branch, check it out before running `poetry install`.

## Polylith Architecture

Polylith projects compose reusable **components** (business logic) and **bases** (entry points). Each deployable service or distributable library is defined in `projects/<project-name>/`, with its own `pyproject.toml`, dependencies, version, and included bricks.

The project's `[tool.polylith.bricks]` mappings identify reusable code; `[tool.poetry].packages` entries include code from the shared `components/` and `bases/` directories. See the [Polylith project documentation](https://davidvujic.github.io/python-polylith-docs/projects/).

### Synchronizing Poetry Packages

After changing a project's `[tool.polylith.bricks]` mappings, regenerate its `[tool.poetry].packages` entries:

```bash
# Run from the repository root with Python 3.11 or newer.
python sync_poetry_packages.py --toml projects/open-access-api/pyproject.toml
```

The script modifies the specified TOML file in place and derives each `include` and `from` entry from the brick mappings. **Review the diff before building the project wheel.** This updates package inclusion only; it does not synchronize dependencies or update lock files.

### Building Projects

Build a project from the repository root using the Poetry Multiproject plugin:

```bash
poetry build-project --directory projects/<project_name>
```

This collects the configured bricks into a wheel and source distribution in that project's `dist/` directory. Use `build-project` to handle relative package paths. See [Polylith packaging and deployment](https://davidvujic.github.io/python-polylith-docs/deployment/).

### Project Versioning

Projects are versioned independently using the `version` field in their `[project]` section. Follow `MAJOR.MINOR.PATCH` versioning for breaking changes, backward-compatible features, and fixes respectively.

```bash
poetry version patch --directory projects/<project-name>
```

Use `minor`, `major`, or an explicit version where appropriate. Update the project's changelog where present and rebuild after version changes. Changes to shared bricks may require releases of multiple dependent projects.

See the [Poetry version command](https://python-poetry.org/docs/cli/#version).

### Publishing Projects

Build with the Multiproject plugin, inspect the distribution files, and then publish with Poetry credentials configured for the destination repository:

```bash
poetry build-project --directory projects/<project_name>
# Inspect the project's dist/ directory before publishing.
poetry publish --directory projects/<project_name>
```

Use `--repository <repository-name>` for a configured alternative repository. Ensure `dist/` contains only the intended artifacts. Keep building and publishing as separate steps so Polylith's relative brick paths are handled by the build plugin.

See [Poetry publish](https://python-poetry.org/docs/cli/#publish) and [repository configuration](https://python-poetry.org/docs/repositories/).

## Dependency Notes

### SQLAlchemy Async Support and `greenlet`

Projects importing `sqlalchemy.ext.asyncio` must declare the `asyncio` extra in the **project's own** dependencies, so installing its distribution also installs `greenlet`:

```toml
# Project dependencies (PEP 621)
dependencies = [
    "sqlalchemy[asyncio] (>=2.0.40,<3.0.0)",
]
```

The root Poetry configuration expresses the same requirement as:

```toml
[tool.poetry.dependencies]
sqlalchemy = { version = "^2.0.40", extras = ["asyncio"] }
```

**The root dependency declaration does not supply dependencies to a separately built project wheel.** Declare the extra in each relevant project's `pyproject.toml`.

Otherwise, a clean Docker installation may fail at startup with `ModuleNotFoundError: No module named 'greenlet'` or an SQLAlchemy async import error.

After updating project dependencies, rebuild the wheel and Docker image and **recreate the API container**. Restarting an existing container does not replace its installed dependencies.

## PR Checks and Formatting

The **Python quality** GitHub Action:

- Validates syntax in tracked Python files, including malformed f-strings, before formatting.
- Excludes `development/**` and `**/alembic/versions/**` from its checks and formatting.
- Fails on syntax errors.
- Reports unused imports through Ruff as warnings without automatically fixing them or failing the action.

For PRs originating from this repository, isort and Black use the root `pyproject.toml` rules and commit formatting changes to the PR branch. Fork PRs receive formatting checks without automatic modifications.

The **Python quality comment** workflow posts or updates a log comment mentioning the PR author, including for validation failures. Long logs are truncated in the comment; the complete report is available as a workflow artifact. The reporting workflow must be on the default branch to run.

## TOML Organization

Poetry manages dependencies but does not necessarily maintain the preferred ordering of TOML keys or lists of included Polylith bricks. Install `toml-sort` through pipx:

```bash
pipx install toml-sort
```

Run it on a TOML file as needed:

```bash
toml-sort --sort-first "project,tool,name,homepage,repository,packages" pyproject.toml
```

## Local FastAPI Development

For background on hot reloading FastAPI services in a Polylith repository, see [FastAPI microservices with Polylith](https://davidvujic.blogspot.com/2023/07/python-fastapi-microservices-with-polylith.html).

Consult each project's own configuration for its current run and reload commands.

## VS Code Recommendations

- [Microsoft Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)
- [indent-rainbow](https://marketplace.visualstudio.com/items?itemName=oderwat.indent-rainbow)
- [autoDocstring](https://marketplace.visualstudio.com/items?itemName=njpwerner.autodocstring)
- [Even Better TOML](https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml)

Configure autoDocstring to use Google-style docstrings.

## Coding Conventions

Follow [PEP 8](https://peps.python.org/pep-0008/) and the existing repository conventions.

### Naming

- Files, directories, functions, and variables: `snake_case`
- Classes: `UpperCamelCase`
- Constants: `UPPER_SNAKE_CASE`

### Documentation

Document public functions, classes, and packages with [Google-style docstrings](https://google.github.io/styleguide/pyguide.html#docstrings). For nontrivial functions, describe purpose, arguments, return values, and raised exceptions. Simple accessors may use a short summary or no docstring when self-explanatory.

Attribute third-party code and externally sourced implementations, including code adapted from GitHub, Stack Overflow, or AI-assisted responses, with a source URL or other relevant reference where appropriate.

### Logging and Types

- Use Python's `logging` module for progress and diagnostic messages.
- Use type annotations where practical.
- Use enums for values drawn from a controlled vocabulary.

### Classes

The previous development guidelines emphasize encapsulation and documented interfaces for class-based code. When working on existing classes, follow their established public/protected/private naming conventions and avoid unnecessary API changes.

- Prefix internal methods and attributes with `_` or `__` as appropriate to the existing design.
- Provide appropriate access through public methods or properties.
- Preserve existing logger, debug/verbosity, and string-representation conventions where present.
- Favor consistency with the surrounding code over introducing unrelated refactors.
