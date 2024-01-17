''' helpers for argparse args, including custom eactions '''

import json
from argparse import ArgumentTypeError
from typing import Dict

def json_type(value: str) -> Dict:
    """
    convert to JSON and return a dict

    Args:
        value (str): JSON string

    Raises:
        argparse.ArgumentTypeError: 

    Returns:
        _type_: _description_
    """
    try:
        return json.decodes(value)
    except:
        raise ArgumentTypeError("Invalid JSON: " + value)
    