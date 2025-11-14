# Copilot Instructions for niagads-pylib

## Rules

-   remember to review codebase (either files in same or parent folder or all files in context) when implementing new files to keep conventions, style and big picture of the project instead of writing generic code solutions
-   pay attention to formatting, making sure that new code is not necessarily inserted at current cursor but where it logically flows in the existing files
-   don't lecture; just focus on explicit tasks/requests. Only make suggestions when asked directly or when there are multiple paths that need to be evaluated. Provide minimum description unless more information is requested.
-   always add extra blank spaces between large code blocks to improve readability
-   don't remove existing blank spaces in code
-   only alter comments if either requested or necessary for explaning code modifications, additions, etc

## Project Overview

-   **niagads-pylib** is a monorepo of Python packages, utilities, and services supporting NIAGADS genomics projects.
-   Uses the [Polylith architecture](https://polylith.gitbook.io/polylith) for modularity; bricks (components, bases, projects) are organized in subfolders.
-   Managed with [Poetry](https://python-poetry.org/) and [Python-polylith toolkit](https://davidvujic.github.io/python-polylith-docs/).

## Key Directories

-   `components/niagads/` — Core reusable modules (e.g., `utils`, `database`, `csv_parser`, etc.)
-   `bases/niagads/` — Service entry points and tools
-   `projects/` — Example apps, schema managers, API services
-   `development/` — Experimental and test code
-   `docs/` — Sphinx documentation (deprecated / ignore)

## Developer Workflows

-   **Setup:**
    -   Use Python 3.12+ and Poetry.
    -   Install with `poetry install` in repo root.
-   **Linting:**
    -   VSCode task: `flake8-whole-project` only to look for things like malformed f-strings; don't do normally as it conflicts with black formatter.
-   **Testing:**
    -   Run `pytest` (configured for verbose output via `pyproject.toml`). Obsolete. Ignore for now.
-   **TOML Sorting:**
    -   Use `toml-sort` to keep `pyproject.toml` organized: `toml-sort --sort-first "project,tool,name,homepage,repository,packages" pyproject.toml`. Ignore this; should be done by developers as needed manually for now. Will later add to github as automated task on PR

## Coding Conventions

-   **Naming:**
    -   Files, directories, functions, variables: `snake_case`
    -   Classes: `UpperCamelCase`
    -   Constants: `UPPER_SNAKE_CASE`
-   **Docstrings:**
    -   Use [Google style](https://google.github.io/styleguide/pyguide.html#docstrings)
    -   Credit all third-party or AI-generated code with source URLs in docstrings
-   **Classes:**
    -   Prefer encapsulation: private (`__var`) and protected (`_var`) members
    -   All classes should inherit from the `ComponentBaseMixin` definied in `components/niagads/common/core.py`
    -   Override `__str__` for debugging
-   **Type Hints:**
    -   Use type hints and `enums` for controlled vocabularies

## Integration & Patterns

-   **External dependencies:** Managed via Poetry in `pyproject.toml` (`[tool.poetry.dependencies]`)
-   **Service boundaries:** Bases provide service entry points; components are reusable bricks
-   **Logging:** Use Python `logging` module; all classes should expose a logger; please use the `FunctionContextLoggingWrapper` to apply formatting and tack function context onto logging statement

## Examples

-   See `components/niagads/utils/` for utility patterns
-   See `bases/niagads/genomicsdb_service/` for service entry points
-   See `projects/` for integration examples

---

For unclear conventions or missing documentation, ask maintainers for clarification. Update this file as new patterns emerge.
