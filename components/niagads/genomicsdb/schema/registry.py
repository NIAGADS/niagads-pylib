from typing import Dict, Type
from sqlalchemy.orm import DeclarativeMeta


class TableRegistry:
    """
    Registry mapping SQLAlchemy ORM (declarative) classes to their names, schemas, etc.
    Usage:
        # Register using class name as key or supply a name to register to override (e.g., for MVs)
        @TableRegistry.register()
        class MyModel(Base, Mixins...):
    """

    _registry: Dict[str, DeclarativeMeta] = {}

    @classmethod
    def register(cls, name: str = None):
        def decorator(base_cls: DeclarativeMeta) -> DeclarativeMeta:
            key = name or base_cls.__name__
            cls._registry[key.upper()] = base_cls
            return base_cls

        return decorator

    @classmethod
    def get_table_class(cls, name: str) -> DeclarativeMeta:
        return cls._registry[name.upper()]

    @classmethod
    def get_table_package(cls, name: str) -> str:
        return cls.get_table_class(name).__module__  # .replace("components.", "")

    @classmethod
    def get_table_metadata(cls, name: str):
        """Return the SQLAlchemy MetaData object for a given table."""
        return cls._registry[name.upper()].metadata

    @classmethod
    def get_table_schema(cls, name: str):
        """Return the schema for a given table."""
        return cls._registry[name.upper()].schema

    @classmethod
    def get_registered_tables(cls):
        """
        Return a list of all registered ORM (declarative) classes.

        Returns:
            list[DeclarativeMeta]:
                List of registered ORM classes
        """
        return list(cls._registry.values())

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a table is registered."""
        return name.upper() in cls._registry
