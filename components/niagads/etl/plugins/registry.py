from typing import Callable, Dict, List, Optional, Type, Union

from niagads.etl.plugins.base import AbstractBasePlugin


class PluginRegistry:
    """
    Registry mapping plugin class names -> classes.
    Provides introspection for CLI.
    """

    _registry: Dict[str, Type[AbstractBasePlugin]] = {}
    _meta: Dict[str, dict] = {}

    @classmethod
    def register(
        cls,
        plugin_cls: Union[Type[AbstractBasePlugin], None] = None,
        *,
        metadata: Optional[dict] = None,
    ) -> Callable:
        """
        Can be used as:
            @PluginRegistry.register
            class MyPlugin(AbstractBasePlugin): ...

        Or with metadata:
            @PluginRegistry.register(metadata={"version": "1.0"})
            class MyPlugin(AbstractBasePlugin): ...
        """

        def decorator(inner_cls: Type[AbstractBasePlugin]) -> Type[AbstractBasePlugin]:
            key = inner_cls.__name__
            cls._registry[key] = inner_cls
            cls._meta[key] = metadata or {}
            return inner_cls

        if plugin_cls is None:
            return decorator  # used with parentheses
        return decorator(plugin_cls)  # used directly

    @classmethod
    def get(cls, name: str) -> Type[AbstractBasePlugin]:
        """
        Retrieve a registered plugin class by name.

        Args:
            name (str): The name of the plugin class.

        Returns:
            Type[AbstractBasePlugin]: The plugin class.

        Raises:
            KeyError: If the plugin is not found in the registry.
        """
        if name not in cls._registry:
            raise KeyError(f"Plugin '{name}' not found")
        return cls._registry[name]

    @classmethod
    def list_plugins(cls) -> List[str]:
        """
        List all registered plugin class names.

        Returns:
            List[str]: Sorted list of registered plugin class names.
        """
        return sorted(cls._registry.keys())

    @classmethod
    def describe(cls, name: str) -> dict:
        """
        Get metadata and parameter model schema for a registered plugin.

        Args:
            name (str): The name of the plugin class.

        Returns:
            dict: Metadata dictionary including parameter model schema and affected tables.

        Raises:
            KeyError: If the plugin is not found in the registry.
            RuntimeError: If parameter model or affected tables cannot be retrieved.
        """
        if name not in cls._registry:
            raise KeyError(f"Plugin '{name}' not found")
        plugin_cls: AbstractBasePlugin = cls._registry[name]
        meta = cls._meta.get(name, {}).copy()
        meta.setdefault("class", name)
        try:
            params_model = plugin_cls.parameter_model()
            meta["parameter_model"] = params_model.model_json_schema()
        except Exception as e:
            raise RuntimeError(
                f"Failed to get parameter_model for plugin '{name}': {e}"
            )
        try:
            meta["affected_tables"] = plugin_cls().affected_tables
        except Exception as e:
            raise RuntimeError(
                f"Failed to get affected_tables for plugin '{name}': {e}"
            )
        try:
            meta["description"] = plugin_cls().description
        except Exception as e:
            raise RuntimeError(f"Failed to get description for plugin '{name}': {e}")
        return meta
