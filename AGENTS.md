# AI & Copilot Code Change Policy

## Build system

* This Python Monorepo is implemented using the Polylith Architecture, managed using poetry

## Code Change Requirements

* All code changes must strictly follow Python and PEP8 coding and line length conventions and requirements in this file.
* Any deviation from these rules should be considered a bug and corrected immediately.
* AI-generated code must be reviewed for formatting, style, and logical placement before submission.

## Implementation Checklist

* Avoid redundant code and helper functions that unnecessarily wrap single lines of code
* Before adding code, search for and reuse existing project utilities, components, and Pydantic models that fit the task.
* Always review and match project conventions, formatting, and style.
* Place imports, constants, and docstrings in logical order.
* Avoid duplicate imports and code blocks.
* Use idiomatic Python and PEP8 formatting.
* Use Pydantic 2+ where the project’s existing design or the request calls for it. Do not replace established Pydantic models with dictionaries or duplicate validation.
* Add extra blank spaces between large code blocks for readability.
* Never take credit for user changes.
* Only alter comments if either requested or necessary for documenting core code modifications, additions, etc.
* Do not do inline imports unless necessary to avoid circular imports in the package.
* Avoid nested function defintions unless absolutely necessary.
* Ensure docstrings and comments are concise, relevant, and professional—focused on what the function does and why, not its visibility or trivial details.
* Do not invent fallback defaults that hide missing, invalid, or failed data. Follow the project’s established error-handling behavior.
* Implement only the requested behavior. Do not add abstractions or support for unrequested use cases.
* Before creating a class or adding class behavior, inspect nearby code and search the project for relevant base classes and mixins. Reuse applicable project mixins, combining them with ComponentBaseMixin as required. Create a new mixin only when the behavior is reusable across multiple classes and no existing mixin provides it; otherwise keep the behavior in the class. Don’t duplicate behavior already provided by a mixin.

## Performance Considerations

* Add checks and defensive handling only for conditions that can occur in the requested use case or are required by the project.  Too many unneccessary checks can slow down.  My code deals with Enterprise Scale data.
* Avoid repeated iterations over data structures when the work can be done in one pass or with an existing project utility.
* Consider parallelization for iterations over large data.

## Additional Requirements

* Always use python best practices when inserting new code.
* Review codebase (files in same or parent folder, or all files in context) when implementing new files to keep conventions, style, and big picture of the project instead of writing generic code solutions.
* Pay attention to formatting, making sure that new code is not necessarily inserted at current cursor but where it logically flows in the existing files.
* Do not lecture; just focus on explicit tasks/requests. Only make suggestions when asked directly
* Always aske for clarification when there are multiple paths that need to be evaluated or context is unclear.
* If project instructions, configuration, and existing code patterns conflict, follow the explicit instruction or configuration that applies to the task. Don’t copy a nearby pattern that contradicts it.
* After editing, review the diff and run the relevant focused checks. Report any checks that could not be run.

# Copilot Instructions for niagads-pylib

## Project Overview

* **niagads-pylib** is a monorepo of Python packages, utilities, and services supporting NIAGADS genomics projects.
* Uses the [Polylith architecture](https://polylith.gitbook.io/polylith) for modularity; bricks (components, bases, projects) are organized in subfolders.
* Managed with [Poetry](https://python-poetry.org/) and [Python-polylith toolkit](https://davidvujic.github.io/python-polylith-docs/).

## Key Directories

* `components/niagads/` — Core reusable modules (e.g., `utils`, `database`, `csv_parser`, etc.)
* `bases/niagads/genomicsdb_service/etl/plugins` - GenomicsDB ETL plugins
* `bases/niagads/` — Service entry points and tools
* `projects/` — Example apps, schema managers, API services
* `development/` — Experimental and test code
* `docs/` — Sphinx documentation (deprecated / ignore)

## Developer Workflows

### Linting

* respect `black` and `isort` conventions

#### ETL Plugins

* see `bases/niagads/genomicsdb_etl/README.md` for general plugin implementation guidelines
* see `bases/niagads/genomicsdb_etl/plugins/` for example plugins

## Coding Conventions

* **Naming:**
  * Files, directories, functions, variables: `snake_case`
  * Classes: `UpperCamelCase`
  * Constants: `UPPER_SNAKE_CASE`
* **Docstrings:**
  * Use [Google style](https://google.github.io/styleguide/pyguide.html#docstrings)
  * Credit all third-party code with source URLs in docstrings
* **Classes:**
  * Prefer encapsulation: private (`__var`) and protected (`_var`) members
  * All classes must inherit from `ComponentBaseMixin` (`components/niagads/common/core.py`), except enums and Pydantic models. When modifying legacy code, add the mixin to any class you touch if doing so is compatible with its existing design. Don’t undertake unrelated migrations solely to add the mixin.
  * Pydantic models that will be serialized for output and/or tied to either the APIs or logged or converted to SQLAlchemy data models during ETL processing must inherit from `CustomBaseModel` (`components/niagads/common/models/base.py`)
  * Add **repr** or **str** only when useful and consistent with existing project patterns.
* **Type Hints:**
  * Use type hints and `enums` for controlled vocabularies
* **Enums:**
  * use `enums` for controlled vocabulary, for string enums, use `CaseInsensitiveEnum` defined in `components/niagads/enums/core.py`

## Integration & Patterns

* **External dependencies:** Managed via Poetry in `pyproject.toml` (`[tool.poetry.dependencies]`)
* **Service boundaries:** Bases provide service entry points; components are reusable bricks
* **Scripts:** All project scripts are encapsulated classes (e.g., `bases/niagads/sql_runner/core.py`) that inherite from ComponentBaseMixin.
* **Logging:** ComponentBaseMixin initializes loggers.

## Examples

* See `components/niagads/utils/` for utility patterns
* See `projects/` for integration examples

---

For unclear conventions or missing documentation, ask maintainers for clarification. Update this file as new patterns emerge.
