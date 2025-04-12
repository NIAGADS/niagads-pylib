"""string
The `string` module provides a library of
string manipulation functions, converters and
value testers
"""

import nh3
import hashlib
import json
import re

from typing import List
import uuid
from dateutil.parser import parse as parse_date
from datetime import datetime


def sanitize(htmlStr: str) -> str:
    """
    ammonia sanitization that turns a string into unformatted HTML.
    used to sanitize incoming API query and path arguments

    Args:
        htmlStr (str): string to be cleaned

    Returns:
        str: cleaned string
    """
    if htmlStr is not None:
        return nh3.clean_text(htmlStr.strip())

    return htmlStr


def generate_uuid(value: str):
    """Generates a unique ID (UUID) from a string using SHA-256 hashing.

    Args:
        value(str): The string to generate a unique ID from.

    Returns:
        A UUID object representing the unique ID.
    """
    hashedString = hashlib.sha256(value.encode()).hexdigest()
    return uuid.uuid5(uuid.NAMESPACE_DNS, hashedString)


def blake2b_hash(value: str, size: int = 20):
    """hash a string using blake2b hashing.

    Args:
        value(str): The string to generate a unique ID from.
        size (str): digest size

    Returns:
        A UUID object representing the unique ID.
    """
    hashedString = hashlib.blake2b(value.encode(), digest_size=size).hexdigest()
    return hashedString


def list_to_string(value, nullStr="NULL", delim=","):
    """checks if list, if so, converts to string;
    None/empty -> nullStr;
    all other return str(value)
    """
    if value is None or len(value) == 0:
        return nullStr

    if isinstance(value, list):
        return delim.join([xstr(v, nullStr=nullStr) for v in value])

    return xstr(value)


def string_in_list(value: str, array: List[str], ignoreCase=False):
    """
    wrapper for seeing if a string value is 'in' a list
    allows case insensitive matches

    Args:
        value (str): string value to lookup
        array (List[str]): list of strings
        ignoreCase (bool, optional): flag for case sensitive match. Defaults to False.
    """
    if not ignoreCase:
        return value in array
    else:
        if value.casefold() in (s.casefold() for s in array):
            return True
    return False


def eval_null(value: str, naIsNull=False):
    """
    checks to see if value is NULL / None or equivalent

    Args:
        value (str): value to evaluate
        naIsNull (boolean, optional): NA is considered null.  Default to False

    Returns:
        None if null value, else value
    """
    if value is not None and is_null(value, naIsNull=naIsNull):
        return None
    return value


def dict_to_info_string(obj):
    """wrapper for dict_to_string (semantics )
    in string utils to avoid circular imports"""
    return dict_to_string(obj, ".")


def dict_to_string(obj, nullStr, delimiter=";"):
    """translate dict to attr=value; string list
    in string utils to avoid circular imports
    """
    pairs = [k + "=" + xstr(v, nullStr=nullStr) for k, v in obj.items()]
    pairs.sort()
    return delimiter.join(pairs)


def reverse(s):
    """reverse a string
    see https://www.w3schools.com/python/python_howto_reverse_string.asp"""
    return s[::-1]


def truncate(s, length):
    """
    if string s is > length, return truncated string
    with ... added to end
    """
    return (s[: (length - 3)] + "...") if len(s) > length else s


def xstr(value, nullStr="", falseAsNull=False, dictsAsJson=True):
    """
    wrapper for str() that handles Nones,
    lists, and dict objects

    Args:
        value (obj): obj / type to be converted to string
        nullStr (str, optional): value to used to indicate NULL/None. Defaults to "".
        falseAsNull (bool, optional): treat `False` as None. Defaults to False.
        dictsAsJson (bool, optional): convert dicts to JSON, otherwise generates
        an INFO string (semi-colon delimited key=value pairs). Defaults to True.
        if nullStr is "" and dictAsJson=False, '.' will be used in the info string
        for None values

    Returns:
        value in string format
    """
    if value is None:
        return nullStr

    if isinstance(value, list):
        if len(value) == 0:
            return nullStr
        else:
            return ",".join([xstr(v, nullStr, falseAsNull, dictsAsJson) for v in value])

    if isinstance(value, dict):
        if bool(value):
            if dictsAsJson:
                return json.dumps(value)
            else:
                return dict_to_string(value, nullStr=".")
        else:
            return nullStr

    if falseAsNull and isinstance(value, bool):
        if value is False:
            return nullStr
        else:
            return str(value)

    if is_date(value):
        return to_date(value, returnStr=True)

    return str(value)


# FIXME: try/catch for non numeric types
def to_date(value, pattern="%Y-%m-%d", returnStr=False):
    """converts a string into a Python date time object or reformat existing datetime object

    Args:
        value (string): value to be converted
        pattern (str, optional): date format to be returned if returnStr. Defaults to '%m-%d-%Y'.
        returnStr (bool, optional): return string? if False returns a date time object. Defaults to False.

    Returns:
        datetime object if returnStr is False
        formatted string (following pattern) if returnStr is True
    """
    date = value if isinstance(value, datetime) else parse_date(value, fuzzy=True)
    return date.strftime(pattern) if returnStr else date


def to_bool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    modified from https://stackoverflow.com/a/18472142
    """
    val = val.lower()
    if val in ("y", "yes", "t", "true", "1"):
        return 1
    elif val in ("n", "no", "f", "false", "0"):
        return 0
    else:
        raise ValueError("Invalid boolean value %r" % (val,))


def is_bool(value):
    """checks if value is a boolean"""
    if isinstance(value, bool):
        return True

    try:
        to_bool(value)
        return True
    except:
        return False


def is_date(value, fuzzy=False):
    """Return whether the string can be interpreted as a date.
    from https://stackoverflow.com/a/25341965

    Args:
        value (str): string to check for date
        fuzzy (bool, optional):ignore unknown tokens in string if True. Defaults to False.

    Returns:
        bool: flag indicating if string is date (or contains date if fuzzy=True)
    """
    if is_numeric(value):  # catch ints and floats
        return False

    if isinstance(value, datetime):
        return True

    try:
        parse_date(value, fuzzy=fuzzy)
        return True

    except:
        return False


def is_numeric(value):
    """legacy for `is_number`"""
    return is_number(value)


def is_number(value):
    """check if the string is a number;
    support legacy code originally written for Python 2.7"""
    # extra is_float if string is to check for scientific notation
    return (
        value.isnumeric() or is_float(value)
        if isinstance(value, str)
        else is_integer(value) or is_float(value)
    )


def is_integer(value):
    """check if the string is an integer"""
    if isinstance(value, (float, bool)):
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


def is_float(value):
    """check if the string is a float"""
    try:
        float(value)
        return True
    except ValueError:
        return False


def is_non_numeric(value):
    """checks if string is non-numeric; legacy to support code written for Python 2.7"""
    return not is_number(value)


def to_number(value):
    """convert string to appropriate number"""
    try:
        return int(value)
    except ValueError:
        return (
            int(float(value)) if float(value).is_integer() else float(value)
        )  # raises ValueError again that will be thrown


def to_numeric(value):
    """legacy  `to_number`"""
    return to_number(value)


def is_null(value: str, naIsNull: bool = False):
    """
    check to see if string contains a value that could be interpreted as null/undefined

    Args:
        value (str): string value to check
        naIsNull (bool, optional): flag if `NA` values should be interpreted as `NULL`. Defaults to False.

    Returns:
        bool: True if value is_null
    """
    if value is None or value in ["NULL", "null"]:
        return True
    if naIsNull and string_in_list(
        value,
        ["NA", "not reported", "not applicable", ".", "N/A", "NULL"],
        ignoreCase=True,
    ):
        return True
    return False


def is_camel_case(s):
    """relaxed check for camel case b/c allows things like cRGB"""
    return s != s.lower() and s != s.upper() and "_" not in s


def to_snake_case(key):
    """converts camel case or space delimited strings to snake case
    from https://stackoverflow.com/a/1176023 / advanced cases"""
    return (
        re.regex_replace("([a-z0-9])([A-Z])", r"\1_\2", key).lower().replace(" ", "_")
    )


def int_to_alpha(value, lower=False):
    """Convert an input integer to alphabetic representation,
    starting with 1=A. or 1=a if lower=True"""

    if lower:
        return chr(96 + value)
    else:
        return chr(64 + value)


def ascii_safe_str(obj):
    """convert to ASCII safe string"""
    try:
        return str(obj)
    except UnicodeEncodeError:
        return obj.encode("ascii", "ignore").decode("ascii")


def is_balanced(value, start="(", end=")"):
    """returns True if enclosing tags are balanced (e.g, braces, brackets, parentheses, carets, user defined)
    modified from https://www.geeksforgeeks.org/identify-mark-unmatched-parenthesis-expression/

    TODO: (possibly) handle multiple, nested kinds of tags, e.g., ([{}])

    Args:
        value (str): string to check

    Returns:
        boolean indicating whether or not parentheses are balanced
    """
    stack = []
    for c in value:
        # if c is opening tag then push into stack
        if c == start:
            stack.append(c)
        elif c == end:
            # unmatched start tag; return False
            if len(stack) == 0:
                return False
            else:  # matched start tag
                stack.pop()

    if len(stack) == 0:  # balanced
        return True
    else:  # not balanced
        return False


# regex wrappers to re calls to reduce re imports
# =================================================
def regex_replace(pattern, replacement, value, **kwargs):
    """
    wrapper for `re.sub`

    Args:
        pattern (str): regular expression pattern to match
        replacement (str):string to substitute for pattern
        value (str): original string
        **kwargs (optional): optional keyword arguments expected by `re.sub`:
            `count`: maximum number of patterns to be replaced
            `flags`: (e.g., IGNORECASE)
                see https://docs.python.org/3/library/re.html#re.RegexFlag;
                can import from `niagads.utils.RegexFlag`
                Defaults to NOFLAG (0).

    Returns:
        updated string
    """
    return re.sub(pattern, replacement, value, **kwargs)


def regex_extract(pattern, value, firstMatchOnly=True, **kwargs):
    """
    wrapper for `re.search`

    Args:
        pattern (str): regular expression pattern to match
        value (str): string to search
        **kwargs (optional): optional keyword arguments expected by `re.search`:
            `flags`: (e.g., IGNORECASE)
                see https://docs.python.org/3/library/re.html#re.RegexFlag;
                can import from `niagads.utils.RegexFlag`
                Defaults to NOFLAG (0).

    Returns:
        string containing first match if firstMatchOnly, else list of all pattern matches
    """
    if firstMatchOnly:
        result = re.search(pattern, value, **kwargs)

        if result is not None:
            try:
                return result.group(1)
            except:
                return result.group()
        return None

    else:
        result = re.findall(pattern, value, **kwargs)
        return None if len(result) == 0 else result


def matches(pattern, value, **kwargs):
    """
    checks if string contains a pattern

    Args:
        pattern (str): regular expression pattern to match
        value (str): string to search
        **kwargs (optional): optional keyword arguments expected by `re.search`:
            `flags`: (e.g., IGNORECASE)
                see https://docs.python.org/3/library/re.html#re.RegexFlag;
                can import from `niagads.utils.RegexFlag`
                Defaults to NOFLAG (0).

    Returns:
        True if match is found
    """
    result = re.search(pattern, value, **kwargs)
    return result is not None


def regex_split(pattern, value, **kwargs):
    """
    wrapper for `re.split`

    Args:
        pattern (str): regular expression pattern to match
        value (str): string to search
        **kwargs (optional): optional keyword arguments expected by `re.split`:
            `maxsplit`: if maxsplit is non-zero than at most, maxsplit splits will be done
            `flags`: (e.g., IGNORECASE)
                see https://docs.python.org/3/library/re.html#re.RegexFlag;
                can import from `niagads.utils.RegexFlag`
                Defaults to NOFLAG (0).

    """
    return re.split(pattern, value, **kwargs)
