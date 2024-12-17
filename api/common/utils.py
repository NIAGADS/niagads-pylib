from typing import Any

def get_attribute(obj: Any, key: str, default: Any=None):
    """
    get and getattr do not always work as expected for Pydantic models: 'private': _attr, field name collisions
    sometimes get a KeyError instead of returning the default, even when this is not the case

    Args:
        obj (Any): the object
        key (str): attribute name
        default (Any): default value
    """
    if key in obj:
        return obj[key]
    else:
        return default
