"""string
The `string` module provides a library of 
string manipulation functions, converters and 
value testers
"""

import re
from dateutil.parser import parse as parse_date
from datetime import datetime

import niagads.utils.dict as dict_utils # avoid circular import by using the full import path


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
    elif isinstance(value, list):
        if len(value) == 0:
            return nullStr
        else:
            return ','.join([xstr(v, nullStr, falseAsNull, dictsAsJson) for v in value])
    elif isinstance(value, dict):
        if bool(value):
            if dictsAsJson:
                return dict_utils.print_dict(value, pretty=False)
            else:
                return dict_utils.dict_to_string(value, nullStr=".")
        else:
            return nullStr
    else:
        return str(value)


def to_date(value, pattern='%m-%d-%Y', returnStr=False):
    """converts a string into a Python date time object

    Args:
        value (string): value to be converted
        pattern (str, optional): date format to be returned if returnStr. Defaults to '%m-%d-%Y'.
        returnStr (bool, optional): return string? if False returns a date time object. Defaults to False.

    Returns:
        datetime object if returnStr is False
        formatted string (following pattern) if returnStr is True
    """
    date = parse_date(value, fuzzy=True) 
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

    if isinstance(value, datetime):
        return True
    
    try: 
        parse_date(value, fuzzy=fuzzy)
        return True

    except ValueError:
        return False


def is_numeric(value):
    ''' legacy for `is_number` '''
    return is_number(value)


def is_number(value):
    ''' check if the string is a number; 
    support legacy code originally written for Python 2.7 '''
    return value.isnumeric()


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
    return not value.isnumeric()


def to_number(value):
    ''' convert string to appropriate number '''
    try:
        return int(value)
    except ValueError:
        return float(value) # raises ValueError again that will be thrown


def is_null(value, naIsNull=False):
    if value is None:
        return True
    if naIsNull and value in ['NA', 'not applicable', 'Not applicable', '.']:
        return True
    return False


def to_snake_case(key):
    ''' converts camel case to snake case
    from https://stackoverflow.com/a/1176023 / advanced cases'''
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', key).lower()



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


# regex wrappers to re calls to reduce re imports
# =================================================
def regex_replace(pattern, replacement, value):
    ''' wrapper for re.sub '''
    return re.sub(pattern, replacement, value)


def regex_extract(pattern, value):
    ''' extract substring using a regexp
        assumes matching a single substring 
        and returns first match
    '''
    result = re.search(pattern, value)
    if result is not None:
        return result.group(1)
    return None

