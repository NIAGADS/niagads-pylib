import importlib
import pkgutil
import re
from typing import Any, Dict, Optional, Union

from niagads.etl.plugins.registry import RegisteredETLProject


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


def register_package_plugins(package_name: str):

    package = importlib.import_module(package_name)
    for _, modname, ispkg in pkgutil.iter_modules(package.__path__):
        if not ispkg:
            importlib.import_module(f"{package_name}.{modname}")


def register_project_plugins(project):
    try:
        package_name = RegisteredETLProject(project).value
    except ValueError as err:
        raise ValueError(
            f"No plugin-package mapping found for project: {project}.  Check `niagads.etl"
        )
    register_package_plugins(package_name)


def register_plugins(
    project: RegisteredETLProject = None,
    packages: Optional[Union[list[str], str]] = None,
):
    """
    Dynamically import all plugins for a list of projects (RegisteredETLProject) and/or a list of package strings to build the registry.

    Args:
        project (RegisteredETLProject, optional):
            Single RegisteredETLProject enum member. If None, no registered project plugins are loaded.
        packages (Union[list[str], str], optional):
            Single package name as string, or a list of package names. If None, no package plugins are loaded.

    Raises:
        RuntimeError: If both arguments are None or empty.
        ValueError: If a project key is not a valid RegisteredETLProject member.
    """

    packages_list = (
        packages
        if isinstance(packages, list)
        else [packages] if packages is not None else []
    )

    if not project and not packages_list:
        raise RuntimeError(
            "At least one of 'project' or 'packages' must be provided and be non-empty."
        )

    if project:
        register_project_plugins(project)

    for package_name in packages_list:
        register_package_plugins(package_name)
