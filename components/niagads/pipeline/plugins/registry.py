from typing import Dict, Type, List, Optional

from niagads.pipeline.plugins.base import AbstractBasePlugin


class PluginRegistry:
    """
    Registry mapping plugin class names -> classes.
    Provides introspection for CLI.
    """

    _registry: Dict[str, Type[AbstractBasePlugin]] = {}
    _meta: Dict[str, dict] = {}

    @classmethod
    def register(
        cls, plugin_cls: Type[AbstractBasePlugin], metadata: Optional[dict] = None
    ):
        """
        Register a plugin class with optional metadata.

        Args:
            plugin_cls (Type[AbstractBasePlugin]): The plugin class to register.
            metadata (Optional[dict]): Optional metadata dictionary for the plugin.

        Returns:
            Type[AbstractBasePlugin]: The registered plugin class.
        """
        key = plugin_cls.__name__
        cls._registry[key] = plugin_cls
        cls._meta[key] = metadata or {}
        return plugin_cls

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
            meta["parameter_model"] = params_model.schema()
        except Exception as e:
            raise RuntimeError(
                f"Failed to get parameter_model for plugin '{name}': {e}"
            )
        try:
            meta["affected_tables"] = (
                plugin_cls().affected_tables
            )  # may require no-arg init
        except Exception as e:
            raise RuntimeError(
                f"Failed to get affected_tables for plugin '{name}': {e}"
            )
        return meta
