"""library of helpers supporting async"""

import contextlib


@contextlib.asynccontextmanager
async def null_async_context():
    """
    Async no-op context manager that yields None.

    Returns:
        None: Always yields None for use in async context management.

    Usage: see components.niagads.etl.plugins.base.py
    """
    yield None
