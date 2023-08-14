""" library of object / dictionary / hash manipulation functions """

import json
from collections import abc
from utils.string_utils import is_float, is_integer
import utils.array_utils as array_utils


def drop_nulls(obj):
    """ find nulls and remove from the object """
    if isinstance(obj, list):
        array_utils.drop_nulls(obj)
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if v}
    

def dict_to_string(obj):
    """ translate dict to attr=value; string list"""
    pairs = [ k + "=" + str(v) for k,v in obj.items()]
    return ';'.join(pairs)


def deep_update(d, u):
    """! deep update a dict
    based on https://stackoverflow.com/questions/3232943/update-value-of-a-nested-dictionary-of-varying-depth/60321833
    answer: https://stackoverflow.com/a/3233356 
    but may not handle all variations

        @param d             source dict to be updated
        @param u             overrides
        @returns             the deep updated source dict
    """
    for k, v in u.items():
        if isinstance(v, abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d



def convert_str2numeric_values(cdict, nanAsStr=True, infAsStr=True):
    """!  converts numeric values in dictionary stored as strings 
    to numeric

        @param cdict             dictionary to conver
        @param nanAsStr          treat NaN/nan/NAN as string?
        @returns                 the converted dictionary
    """
    for key, value in cdict.items():
        if str(value).upper() == 'NAN' and nanAsStr:
            # is_float test will be true for NaN/NAN/nan/Nan etc
            continue
        if 'inf' in str(value).lower() and infAsStr:
            # is_float test will be true for Infinity / -Infinity
            continue
        if is_float(value): # must check float first b/c integers are a subset
            cdict[key] = float(value)
        if is_integer(value):
            cdict[key] = int(value)

    return cdict