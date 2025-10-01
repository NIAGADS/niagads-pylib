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
