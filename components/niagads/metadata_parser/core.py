def is_searchable_string(key, value, skipFieldsWith):
    """
    checks to see if key: value field contains, searchable text
    based on 1) field name and 2) field contents
    """

    if isinstance(value, dict):
        return False

    if isinstance(value, list):
        raise NotImplementedError(
            "need to handle nested string values when looking for searchable text"
        )

    if array_in_string(key, skipFieldsWith):
        return False

    if value is None:
        return False

    if is_bool(value):
        return False

    if is_number(value):
        return False

    return True
