""" library of string manipulation functions """

import re
from dateutil.parser import parse as parse_date
from datetime import datetime


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
    ''' from https://stackoverflow.com/a/1176023 / advanced cases'''
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', key).lower()


# regex wrappers to re calls to reduce re imports
# =================================================
def regex_replace(pattern, replacement, value):
    return re.sub(pattern, replacement, value)


def regex_extract(pattern, value):
    ''' assumes one extract subset only '''
    result = re.search(pattern, value)
    if result is not None:
        return result.group(1)
    return None