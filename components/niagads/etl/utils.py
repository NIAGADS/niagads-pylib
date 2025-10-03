import re
from typing import Any, Dict


def interpolate_params(params: Dict[str, Any], scope: Dict[str, Any]) -> Dict[str, Any]:
    """
    Interpolates string parameters in a dictionary using values from a scope dict.

    Args:
        params (Dict[str, Any]): Dictionary of parameters to interpolate. String values may contain placeholders like ${key}.
        scope (Dict[str, Any]): Dictionary providing values for interpolation.

    Returns:
        Dict[str, Any]: Interpolated parameters dictionary.

    Raises:
        KeyError: If a placeholder key is missing in the scope.
    """

    def repl(val: Any) -> Any:
        """
        Recursively interpolates string values using scope dict.
        """
        if isinstance(val, str):
            for m in re.finditer(r"\$\{([^}]+)\}", val):
                key = m.group(1)
                if key in scope:
                    val = val.replace(m.group(0), str(scope[key]))
                else:
                    raise KeyError(
                        f"Parameter interpolation failed: missing key '{key}' in scope."
                    )
        elif isinstance(val, dict):
            return {k: repl(v) for k, v in val.items()}
        elif isinstance(val, list):
            return [repl(x) for x in val]
        return val

    return {k: repl(v) for k, v in params.items()}


def import_registered_plugins(directories: list[str]):
    """
    Dynamically import all plugins from a list of directories.

    Args:
        directories (list[str]): List of directory paths to search for plugin modules.
            Each directory will be scanned for .py files (excluding dunder files),
            and each file will be imported as a module. This ensures that any plugin
            classes decorated with @PluginRegistry.register are registered.

    Returns:
        None

    Raises:
        None. Invalid directories are skipped silently.
    """
    import importlib.util
    import os
    
    for directory in directories:
        if not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                module_path = os.path.join(directory, filename)
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
