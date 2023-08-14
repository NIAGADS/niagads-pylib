""" library of string manipulation functions & converters"""

import re
from dateutil.parser import parse as parse_date
from datetime import datetime

from niagads.utils.sys_utils import print_dict

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


def xstr(value, nullStr="", falseAsNull=False):
    '''
    wrapper for str() that handles Nones
    '''
    if value is None:
        return nullStr
    elif falseAsNull and isinstance(value, bool):
        if value is False:
            return nullStr
        else:
            return str(value)
    elif isinstance(value, dict):
        if bool(value):
            return print_dict(value, pretty=False)
        else:
            return nullStr
    else:
        return str(value)


def to_date(value, pattern='%m-%d-%Y'):
    # transforms string into Python datetime object
    return parse_date(value, fuzzy=True) # datetime.strptime(value, pattern).date()


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
    '''
    Return whether the string can be interpreted as a date.
    from https://stackoverflow.com/a/25341965
    :param value: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
   
    '''
    if isinstance(value, datetime):
        return True
    
    try: 
        parse_date(value, fuzzy=fuzzy)
        return True

    except ValueError:
        return False


def is_number(value):
    return is_integer(value) or is_float(value)


def is_integer(value):
    if isinstance(value, (float, bool)):
        return False
    try:
        int(value)
        return True
    except ValueError:
        return False


def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False
    

def is_non_numeric(value):
    if True in [char.isdigit() for char in value]:
        return False
    return True


def to_numeric(value):
    ''' convert string to appropriate numeric '''
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

