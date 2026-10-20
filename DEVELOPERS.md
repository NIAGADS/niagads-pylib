# Developer notes

## Synchronizing Poetry packages

After updating a project's `[tool.polylith.bricks]` mappings, run
`sync_poetry_packages.py` to regenerate its `[tool.poetry].packages` list:

```bash
# Run from the repository root with Python 3.11 or newer.
python sync_poetry_packages.py --toml projects/open-access-api/pyproject.toml
```

The script updates the specified TOML file in place, deriving each package's
`include` and `from` values from its brick mapping. Review the diff before
building the project wheel. This synchronizes package inclusion only; it does
not synchronize dependencies or update lock files.

## SQLAlchemy async support and greenlet

Projects that use `sqlalchemy.ext.asyncio` must declare the `asyncio` extra so
installing the project also installs `greenlet`:

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

The root dependency declaration does not supply dependencies to a separately
built project wheel. Include the extra in the project's own `pyproject.toml`.
Without it, a clean Docker installation can fail at startup with
`ModuleNotFoundError: No module named 'greenlet'` and an SQLAlchemy async import
error.

After changing the project dependency, rebuild the wheel and Docker image, then
recreate the API container. Restarting the existing container continues to use
the previously installed dependencies.
