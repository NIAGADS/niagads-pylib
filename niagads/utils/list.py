""" library of array, list, and set manipulation functions """
from collections import OrderedDict, Counter
from .string import xstr


def flatten(array: list):
    ''' flatten nested list ''' 
    # sum(list, []) is a python hack for flattening a nested list
    return sum(array, [])


def chunker(seq, size, returnIterator=True):
    """for a given sequence, splits into even + residual chunks.  returns an iterator 
    see: https://stackoverflow.com/a/434328

    Example:    
        ::
        
            animals = ['cat', 'dog', 'rabbit', 'duck', 'bird', 'cow', 'gnu', 'fish']

            for group in chunker(animals, 3):
                print(group)
        
        will output:
            ['cat', 'dog', 'rabbit']
            ['duck', 'bird', 'cow']
            ['gnu', 'fish']

    Args:
        seq (list): list to be chunked
        size (int): page or chunk size
        returnIterator (boolean, optional): return an iterator; if false, returns a nested list. Defaults to True
        
    Returns:
        iterator for chunked list of lists
    """
    return (seq[pos:pos + size] for pos in range(0, len(seq), size)) if returnIterator \
        else [seq[pos:pos + size] for pos in range(0, len(seq), size)]


def qw(s, returnTuple=False):
    '''
    mimics perl's qw function
    usage: qw('a b c') will yield ['a','b','c']
    returnTuple: return a tuple if true, otherwise return list
    '''
    if returnTuple:
        return tuple(s.split())
    else:
        return s.split()
    

def is_equivalent_list(list1, list2):
    ''' test if two lists contain the same elements;
    order does not matter'''
    return Counter(list1) == Counter(list2)


def is_overlapping_list(list1, list2):
    ''' returns True if the intersection of the two lists is True
    i.e., at least one element in list2 is in list1
    '''
    return bool(set(list1) & set(list2))


def is_subset(list1, list2):
    ''' returns True if list1 is a subset of list2
    i.e., all elements in list1 are in list2'''
    return set(list1).issubset(list2)


def alphabetize_string_list(slist):
    ''' sorts a list of strings alphabetically
    takes a list or a string, but always returns a string
    '''
    if isinstance(slist, str):
        return ','.join(sorted(slist.split(',')))
    else:
        return ','.join(sorted(slist))


def list_to_indexed_dict(clist):
    ''' convert list to hash of value -> index '''
    return OrderedDict(zip(clist, range(1, len(clist) + 1)))


def list_to_string(value, nullStr="NULL", delim=','):
    """ checks if list, if so, converts to string; 
    None/empty -> nullStr; 
    all other return str(value) 
    """
    if value is None or len(value) == 0:
        return nullStr
    
    if isinstance(value, list):
        return delim.join([xstr(v, nullStr=nullStr) for v in value])
    
    return xstr(value)


def drop_nulls(arr):
    """ removes nulls from the list """
    return list(filter(None, arr))


def remove_duplicates(array):
    """ remove duplicates from a list by transforming to set and back """
    return [*set(array)]


def array_in_string(value, array):
    """ check if any element in the array is the string """
    for elem in array:
        if elem in value:
            return True
    return False


def sum_arrays(a, b):
    '''
    calcs per-element sum of two arrays (lists)
    e.g., list a[1,2] + list b[3,4] --> [3,6]
    '''
    return [x + y for x, y in zip(a, b)]


def sum_array_list(arrays):
    '''
    calcs per-element sum for a 
    list of arrays (lists)
    e.g., [[1,2],[3,4]] --> [3,6]
    '''
    return [sum(x) for x in zip(*arrays)]


def average_array_list(arrays):
    '''
    calcs per-element average for
    a list of arrays (lists)
    e.g., [[1,2],[3,4]] --> [1.5,3]
    '''

    n = len(arrays)
    return [float(x) / float(n) for x in sum_array_list(arrays)]
