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
            if key is None and "SchemaBase" not in base_cls.__name__:
                raise ValueError(
                    "Please supply the registered schema name or "
                    "ensure your class name follows the convention `<schema_name>SchemaBase`"
                )

            key = name or base_cls.__name__.replace("SchemaBase", "")
            cls._registry[key.upper()] = base_cls
            return base_cls

        return decorator

    @classmethod
    def get_schema_base(cls, name: str) -> Type[DeclarativeBase]:
        return cls._registry[name.upper()]

    @classmethod
    def get_schema_metadata(cls, name: str):
        """Return the SQLAlchemy MetaData object for a given schema base name."""
        return cls._registry[name.upper()].metadata

    @classmethod
    def get_registered_bases(cls):
        """Return a list of all registered schema base classes."""
        return list(cls._registry.values())

    @classmethod
    def get_registered_metadata(cls):
        """Return a list of all registered SQLAlchemy MetaData objects."""
        return [base.metadata for base in cls._registry.values()]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a schema is registered."""
        return name.upper() in cls._registry
