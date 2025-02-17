"""string
The `string` module provides a library of 
string manipulation functions, converters and 
value testers
"""

import json
import niagads.utils.reg_ex as re

from typing import List
from deprecated import deprecated
from dateutil.parser import parse as parse_date
from datetime import datetime

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
    """ wrapper for dict_to_string (semantics )
    in string utils to avoid circular imports"""
    return dict_to_string(obj, '.')


def dict_to_string(obj, nullStr, delimiter=';'):
    """ translate dict to attr=value; string list
    in string utils to avoid circular imports
    """
    pairs = [ k + "=" + xstr(v, nullStr=nullStr) for k,v in obj.items()]
    pairs.sort()
    return delimiter.join(pairs)


def reverse(s):
    ''' reverse a string 
    see https://www.w3schools.com/python/python_howto_reverse_string.asp '''
    return s[::-1]
        

def truncate(s, length):
    '''
    if string s is > length, return truncated string
    with ... added to end
    '''
    return (s[:(length - 3)] + '...') if len(s) > length else s


def xstr(value, nullStr="", falseAsNull=False, dictsAsJson=True):
    """
    wrapper for str() that handles Nones
    lists and dict objects

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
    elif falseAsNull and isinstance(value, bool):
        if value is False:
            return nullStr
        else:
            return str(value)
    elif is_date(value):
        return to_date(value, returnStr=True)
    elif isinstance(value, list):
        if len(value) == 0:
            return nullStr
        else:
            return ','.join([xstr(v, nullStr, falseAsNull, dictsAsJson) for v in value])
    elif isinstance(value, dict):
        if bool(value):
            if dictsAsJson:
                return json.dumps(value)
            else:
                return dict_to_string(value, nullStr=".")
        else:
            return nullStr
    else:
        return str(value)

# FIXME: try/catch for non numeric types
def to_date(value, pattern='%Y-%m-%d', returnStr=False):
    """converts a string into a Python date time object or reformat existing datetime object

    Args:
        value (string): value to be converted
        pattern (str, optional): date format to be returned if returnStr. Defaults to '%m-%d-%Y'.
        returnStr (bool, optional): return string? if False returns a date time object. Defaults to False.

    Returns:
        datetime object if returnStr is False
        formatted string (following pattern) if returnStr is True
    """
    date = value if isinstance(value, datetime) else \
        parse_date(value, fuzzy=True)    
    return date.strftime(pattern) if returnStr else date



def to_bool(val):
    '''Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    modified from https://stackoverflow.com/a/18472142
    '''
    val = val.lower()
    if val in ('y', 'yes', 't', 'true',  '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', '0'):
        return 0
    else:
        raise ValueError("Invalid boolean value %r" % (val,))
    
    
def is_bool(value):
    ''' checks if value is a boolean '''
    if isinstance(value, bool):
        return True
    
    try:
        to_bool(value)
        return True
    except:
        return False
    

def is_date(value, fuzzy=False):
    """ Return whether the string can be interpreted as a date.
    from https://stackoverflow.com/a/25341965

    Args:
        value (str): string to check for date
        fuzzy (bool, optional):ignore unknown tokens in string if True. Defaults to False.

    Returns:
        bool: flag indicating if string is date (or contains date if fuzzy=True)
    """
    if is_numeric(value): # catch ints and floats
        return False

    if isinstance(value, datetime):
        return True
    
    try: 
        parse_date(value, fuzzy=fuzzy)
        return True

    except:
        return False


def is_numeric(value):
    ''' legacy for `is_number` '''
    return is_number(value)


def is_number(value):
    ''' check if the string is a number; 
    support legacy code originally written for Python 2.7 '''
    # extra is_float if string is to check for scientific notation
    return value.isnumeric() or is_float(value) if isinstance(value, str) \
        else is_integer(value) or is_float(value)


def is_integer(value):
    ''' check if the string is an integer'''
    if isinstance(value, (float, bool)):
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


def is_float(value):
    ''' check if the string is a float '''
    try:
        float(value)
        return True
    except ValueError:
        return False
        

def is_non_numeric(value):
    """checks if string is non-numeric; legacy to support code written for Python 2.7
    """
    return not is_number(value)


def to_number(value):
    ''' convert string to appropriate number '''
    try:
        return int(value)
    except ValueError:
        return int(float(value)) if float(value).is_integer() else float(value) # raises ValueError again that will be thrown


def to_numeric(value):
    """ legacy  `to_number` """
    return to_number(value)


def is_null(value, naIsNull=False):
    if value is None or value in ['NULL', 'null']:
        return True
    if naIsNull and string_in_list(value, ['NA', 'not reported', 'not applicable', '.', 'N/A', 'NULL'], ignoreCase=True):
        return True
    return False


def is_camel_case(s):
    """ relaxed check for camel case b/c allows things like cRGB """
    return s != s.lower() and s != s.upper() and "_" not in s


def to_snake_case(key):
    ''' converts camel case or space delimited strings to snake case
    from https://stackoverflow.com/a/1176023 / advanced cases'''
    return re.regex_replace('([a-z0-9])([A-Z])', r'\1_\2', key).lower().replace(' ', '_')


def int_to_alpha(value, lower=False):
    ''' Convert an input integer to alphabetic representation, 
    starting with 1=A. or 1=a if lower=True'''

    if lower:
        return chr(96 + value)
    else:
        return chr(64 + value)


def ascii_safe_str(obj):
    ''' convert to ASCII safe string '''
    try: return str(obj)
    except UnicodeEncodeError:
        return obj.encode('ascii', 'ignore').decode('ascii')
    

def is_balanced(value, start='(', end=')'):
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
            else: # matched start tag
                stack.pop()
	
    if len(stack) == 0: # balanced
        return True
    else: # not balanced
        return False


# regex wrappers to re calls to reduce re imports
# =================================================
@deprecated(version='0.2.0', reason="Moved; import from `utils.reg_ex` instead")
def regex_replace(pattern, replacement, value, **kwargs):
    ''' see `utils.reg_ex.regex_replace` for documentation '''
    return re.regex_replace(pattern, replacement, value, **kwargs)


@deprecated(version='0.2.0', reason="Moved; import from `utils.reg_ex` instead")
def regex_extract(pattern, value, firstMatchOnly=True, **kwargs): 
    ''' see `utils.reg_ex.regex_extract` for documentation '''
    return re.regex_extract(pattern, value, **kwargs)


@deprecated(version='0.2.0', reason="Moved; import from `utils.reg_ex` instead")
def matches(pattern, value, **kwargs):
    ''' see `utils.reg_ex.matches` for documentation '''
    return re.matches(pattern, value, **kwargs)

@deprecated(version='0.2.0', reason="Moved; import from `utils.reg_ex` instead")
def regex_split(pattern, value, **kwargs):
    ''' see `utils.reg_ex.split` for documentation '''
    return re.regex_split(pattern, value, **kwargs)
