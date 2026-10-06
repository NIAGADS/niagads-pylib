---
name: project-code-review
description: Implement or revise code in this repository using its established standards, utilities, models, and performance patterns. Use for coding tasks.
---

# Project Code Review

## Before coding

1. Read the applicable `AGENTS.md` files and task-specific instructions.
2. Inspect relevant code, tests, configuration, and documentation. For new files, inspect the corresponding package or layer.
3. Search for existing utilities, components, Pydantic models, base classes, and mixins that apply. Reuse them where appropriate.
4. Identify the smallest set of files and behaviors needed to satisfy the request.

If project instructions, configuration, and code patterns conflict, follow the applicable explicit instruction or configuration over a contradictory example. Do not copy a nearby pattern that conflicts with an explicit requirement.

## Implementation

- Make the smallest complete change that satisfies the explicit request.
- Follow the project’s configured Python version, formatting, linting, typing, and line-length rules. Use PEP 8 where project configuration does not specify otherwise.
- Use Pydantic 2 or later when required by the request or the project’s existing design. Do not replace established Pydantic models with dictionaries or duplicate their validation.
- Avoid redundant code and repeated iterations over large data structures when the work can be done in one pass or with an existing project utility.
- Do not invent fallback values that hide missing, invalid, or failed data. Follow the project’s established error-handling behavior.
- Add checks and defensive handling only for conditions that can occur in the requested use case or are required by the project.
- Implement only requested behavior. Do not add abstractions, configuration, compatibility paths, or support for unrequested use cases.
- Preserve unrelated user changes. Keep edits to comments limited to cases where they are requested or needed to explain a code change.
- Do not use inline imports unless needed to avoid a circular import.
- Keep docstrings and comments concise and relevant. Do not add AI attribution or source URLs unless the project requires them.

## Classes and mixins

- All classes must inherit from `ComponentBaseMixin`, except enums and Pydantic models.
- Before creating a class or adding class behavior, inspect nearby code and search the project for relevant base classes and mixins.
- Reuse applicable project mixins and avoid duplicating behavior they provide.
- Create a new mixin only when the behavior is reusable across multiple classes and no existing mixin provides it. Otherwise, keep the behavior in the class.
- When modifying a legacy class, add `ComponentBaseMixin` if compatible with its existing design. Do not modify unrelated classes solely to add the mixin.
- Add `__repr__`, `__str__`, or a class logger when useful and consistent with project patterns; do not add them as boilerplate.

## Project context

- `niagads-pylib` is a Python monorepo using Polylith, Poetry, and the Python-Polylith toolkit.
- `components/niagads/` contains reusable components and utilities.
- `bases/niagads/` contains service entry points and tools.
- `bases/niagads/genomicsdb_etl/plugins` contains GenomicsDB ETL plugins.
- `projects/` contains applications and integrations.
- `development/` contains experimental and test code.
- `docs/` contains deprecated Sphinx documentation; do not update it unless requested.
- Keep code in the appropriate Polylith layer. Bases provide service entry points; reusable functionality belongs in components where consistent with project patterns.
- Manage dependencies through Poetry and the project’s `pyproject.toml`.
- For ETL plugins, follow `bases/niagads/genomicsdb_etl/plugins/README.md`.
- All project scripts are encapsulated classes (e.g., `bases/niagads/sql_runner/core.py`) that inherite from ComponentBaseMixin.
- ComponentBaseMixin initializes loggers.

## Review and checks

Before finishing:

1. Review the diff against the request and applicable instructions.
2. Check for missed existing utilities, models, base classes, or mixins; unnecessary passes over large data; invented defaults; impossible or redundant checks; and unrequested scope.
3. Run focused tests and relevant configured checks when available. Do not run the project’s `flake` tasks.
4. Briefly report what changed and which checks ran. State any relevant checks that could not be run; do not claim checks passed unless they were run.
