""" library of object / dictionary / hash manipulation functions """

import json
import warnings
from collections import abc
from types import SimpleNamespace


def print_dict(dictObj, pretty=True):
    ''' pretty print a dict / JSON object 
    here and not in dict_utils to avoid circular import '''
    if isinstance(dictObj, SimpleNamespace):
        return dictObj.__repr__()
    return json.dumps(dictObj, indent=4, sort_keys=True) if pretty else json.dumps(dictObj)


def get(obj, attribute, default=None, errorAction="fail"):
    """
    retrieve attribute if in dict
    
    Args:
        obj (dict): dictionary object to query
        attribute (string): attribute to return
        default (obj): value to return on KeyError. Defaults to None
        errorAction (string, optional): fail or warn on KeyError. Defaults to False
        
    Returns:
        the value of the attribute or the supplied `default` value if the attribute is missing  
    """
    if errorAction not in ['warn', 'fail', 'ignore']:
        raise ValueError("Allowable actions upon a KeyError are `warn`, `fail`, `ignore`")
    
    try:
        return obj[attribute]
    except KeyError as err:
        if errorAction == 'fail':
            raise err
        elif errorAction == 'warn':
            warnings.warn("KeyError:" + err, RuntimeWarning)
            return default
        else:
            return default


def drop_nulls(obj):
    """ find nulls and remove from the object """
    if isinstance(obj, list):
        return ValueError("Use drop_nulls from the list package to remove nulls from a list/array")
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if v}
    

def deep_update(d, u):
    """
    deep update a nested dict
    based on https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth/60321833
    answer: https://stackoverflow.com/a/3233356 
    TODO: may not handle all variations

    Args:
        d (dict obj): source dict to be updated
        u (dict obj): overrides/updates to be made

    Returns:
        the deep updated source dict
    """
    for k, v in u.items():
        if isinstance(v, abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d



def convert_str2numeric_values(cdict, nanAsStr=True, infAsStr=True):
    """converts numeric values in dictionary stored as strings 
    to numeric

    Args:
        cdict (dict obj): dict bject to convert
        nanAsStr (bool, optional): treat NaN/nan/NAN as string?
        infAsStr (bool, optional): treat inf/INF as string?

    Returns:
        updated dict object
    """
    for key, value in cdict.items():
        if str(value).upper() == 'NAN' and nanAsStr:
            # is_float test will be true for NaN/NAN/nan/Nan etc
            continue
        if 'inf' in str(value).lower() and infAsStr:
            # is_float test will be true for Infinity / -Infinity
            continue
        if value.isnumeric():
            if isinstance(value, float): # must check float first b/c integers are a subset
                cdict[key] = float(value)
            if isinstance(value, int):
                cdict[key] = int(value)
                continue
            if isinstance(value, bool): # treat 0 & 1 as integer, so test last
                cdict[key] = bool(value)

    return cdict


def size(obj, n=0):
    '''
    recursively find size (number of elements) in a potentially nested dict
    after https://www.tutorialspoint.com/How-to-count-elements-in-a-nested-Python-dictionary
    '''
    for key in obj:
        if isinstance(obj[key], dict):
            n = size(obj[key], n + 1)
        else:
            n += 1          
    return n

