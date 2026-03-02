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
            if name is None and "SchemaBase" not in base_cls.__name__:
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
    def get_registered_bases(cls, dependency_schemas: list[str] = None):
        """
        Return a list of all registered schema base classes,
        with dependencies (if any) first in the given order.

        Args:
            dependency_schemas (list[str], optional):
                List of schema names to prioritize first in the result order.
                Defaults to None.

        Returns:
            list[Type[DeclarativeBase]]:
                List of registered schema base classes, with dependencies first
                (if provided), followed by the rest in registration order.
        """
        if not dependency_schemas:
            return list(cls._registry.values())

        reg = cls._registry
        seen = set()
        # Add dependencies in order, if present
        result = [
            cls.get_schema_base(dep)
            for dep in dependency_schemas
            if dep and dep.upper() in reg and not seen.add(dep)
        ]
        # Add the rest, preserving registration order
        result.extend(cls.get_schema_base(key) for key in reg.keys() if key not in seen)
        return result

    @classmethod
    def get_registered_metadata(cls, dependency_schemas: list[str] = None):
        """
        Return a list of all registered SQLAlchemy MetaData objects, with
        dependencies (if any) first in the given order.

        Args:
            dependency_schemas (list[str], optional):
                List of schema names to prioritize first in the result order.
                Defaults to None.

        Returns:
            list[MetaData]:
                List of SQLAlchemy MetaData objects, with dependencies first
                (if provided), followed by the rest in registration order.
        """
        if not dependency_schemas:
            return [base.metadata for base in cls._registry.values()]

        reg = cls._registry
        seen = set()
        # Add dependencies in order, if present
        result = [
            cls.get_schema_metadata(dep)
            for dep in dependency_schemas
            if dep and dep.upper() in reg and not seen.add(dep)
        ]
        # Add the rest, preserving registration order
        result.extend(
            cls.get_schema_metadata(key) for key in reg.keys() if key not in seen
        )
        return result

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Check if a schema is registered."""
        return name.upper() in cls._registry

    @classmethod
    def get_table_class(cls, qualified_table_name: str) -> Type:
        """
        Get the table class for a given 'schema.table' string.

        Args:
            schema_table (str): String in the format 'schema.table'

        Returns:
            Type: The SQLAlchemy table class

        Raises:
            ValueError: If schema_table format is invalid
            KeyError: If schema or table is not found in registry
        """
        try:
            schema_name, table_name = qualified_table_name.split(".", 1)
        except ValueError:
            raise ValueError(
                f"Invalid schema.table format: '{qualified_table_name}'. "
                "Expected format: 'schema_name.table_name'"
            )

        schema_base = cls.get_schema_base(schema_name)

        # Find the table class in the schema base's registry
        for mapper in schema_base.registry.mappers:
            if mapper.class_.__tablename__ == table_name:
                return mapper.class_

        raise KeyError(f"Table '{table_name}' not found in schema '{schema_name}'")
