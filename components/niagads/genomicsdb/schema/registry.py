from typing import Dict, Type
from sqlalchemy.orm import DeclarativeBase


class SchemaRegistry:
    """
    Registry mapping schema names to their DeclarativeBase classes.
    usage:
        # register using class name as key
        @SchemaRegistry.register()
        class ReferenceSchema(DeclarativeBase):
    """

    _registry: Dict[str, Type[DeclarativeBase]] = {}

    @classmethod
    def register(cls, name: str = None):
        def decorator(base_cls: Type[DeclarativeBase]) -> Type[DeclarativeBase]:
            key = name or base_cls.__name__.replace("Schema", "")
            cls._registry[key.upper()] = base_cls
            return base_cls

        return decorator

    @classmethod
    def get_base(cls, name: str) -> Type[DeclarativeBase]:
        return cls._registry[name.upper()]

    @classmethod
    def get_metadata(cls, name: str):
        """Return the SQLAlchemy MetaData object for a given schema base name."""
        return cls._registry[name.upper()].metadata

    @classmethod
    def get_schema(cls, name: str):
        """Return schema name for registered SQLAlchemy Schema model."""
        return cls.get_metadata(name).schema

    @classmethod
    def all_bases(cls):
        """Return a list of all registered schema base classes."""
        return list(cls._registry.values())

    @classmethod
    def all_metadata(cls):
        """Return a list of all registered SQLAlchemy MetaData objects."""
        return [base.metadata for base in cls._registry.values()]

    @classmethod
    def all_schemas(cls):
        """Return a list of all registered SQLAlchemy MetaData objects."""
        return [base.metadata.schema for base in cls._registry.values()]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a schema is registered."""
        return name.upper() in cls._registry
