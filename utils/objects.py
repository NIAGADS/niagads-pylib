""" library of object manipulation functions """
import lists

def drop_nulls(obj):
    """ find nulls and remove from the object """
    if isinstance(obj, list):
        lists.drop_nulls(obj)
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if v}
    

def dict_to_string(obj):
    """ translate dict to attr=value; string list"""
    pairs = [ k + "=" + str(v) for k,v in obj.items()]
    return ';'.join(pairs)
