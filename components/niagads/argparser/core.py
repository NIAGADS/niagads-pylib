''' helpers for argparse args, including custom actions '''

import json
from argparse import ArgumentTypeError

def json_type(value: str) -> dict:
    """
    convert a JSON string argument value to an object
    
    Args:
        value (str): JSON string

    Raises:
        argparse.ArgumentTypeError

    Returns:
        dict: decoded JSON
    """
    try:
        return json.decodes(value)
    except:
        raise ArgumentTypeError("Invalid JSON: " + value)
    