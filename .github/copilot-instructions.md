# AI & Copilot Code Change Policy

## Code Change Requirements

-   All code changes must strictly follow Python and PEP8 coding conventions and requirements in this file.
-   Any deviation from these rules should be considered a bug and corrected immediately.
-   AI-generated code must be reviewed for formatting, style, and logical placement before submission.

## Implementation Checklist

-   Avoid redundant code
-   Always review and match project conventions, formatting, and style.
-   Place imports, constants, and docstrings in logical order.
-   Avoid duplicate imports and code blocks.
-   Use idiomatic Python and PEP8 formatting.
-   Only use Pydantic 2+
-   Add extra blank spaces between large code blocks for readability.
-   Only alter comments if necessary or requested.
-   Never take credit for user changes.
-   Only alter comments if either requested or necessary for explaining code modifications, additions, etc.
-   Do not do inline imports unless necessary to avoid circular imports in the package.
-   Ensure docstrings and comments are concise, relevant, and professional—focused on what the function does and why, not its visibility or trivial details. I

## Additional Requirements

-   Always use python best practices when inserting new code.
-   Review codebase (files in same or parent folder, or all files in context) when implementing new files to keep conventions, style, and big picture of the project instead of writing generic code solutions.
-   Pay attention to formatting, making sure that new code is not necessarily inserted at current cursor but where it logically flows in the existing files.
-   Do not lecture; just focus on explicit tasks/requests. Only make suggestions when asked directly or when there are multiple paths that need to be evaluated. Provide minimum description unless more information is requested.

# Copilot Instructions for niagads-pylib

## Project Overview

-   **niagads-pylib** is a monorepo of Python packages, utilities, and services supporting NIAGADS genomics projects.
-   Uses the [Polylith architecture](https://polylith.gitbook.io/polylith) for modularity; bricks (components, bases, projects) are organized in subfolders.
-   Managed with [Poetry](https://python-poetry.org/) and [Python-polylith toolkit](https://davidvujic.github.io/python-polylith-docs/).

## Key Directories

-   `components/niagads/` — Core reusable modules (e.g., `utils`, `database`, `csv_parser`, etc.)
-   `bases/niagads/genomicsdb_service/etl/plugins` - GenomicsDB ETL plugins
-   `bases/niagads/` — Service entry points and tools
-   `projects/` — Example apps, schema managers, API services
-   `development/` — Experimental and test code
-   `docs/` — Sphinx documentation (deprecated / ignore)

## Developer Workflows

### Linting

-   AI should never prompt to run flake tasks.

#### ETL Plugins

-   see `bases/niagads/genomicsdb_service/etl/plugins/README.md` for general plugin implementation guidelines

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
