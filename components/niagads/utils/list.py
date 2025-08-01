"""library of array, list, and set manipulation functions"""

from collections import OrderedDict, Counter
from typing import List, Union
from niagads.utils.string import xstr


def all_elements_are_none(array):
    """checks if list is all nones"""
    return all(item is None for item in array)


def remove_from_list(arr: list, drop: list):
    """
    Removes all elements listed in drop from an array (list)

    Args:
        arr (list): The list from which elements will be removed.
        drop (list): The list containing elements to remove from arr.

    Returns:
        list: A new list with elements of values removed from arr.
    """
    return [item for item in arr if item not in drop]


def find(array, value, field: str = None, returnValues=True):
    """
    filters a list and returns matches

    Args:
        array (list): the list to filter
        value (any): value to match
        field (str, optional): field name to match if list of objects. Defaults to None.
        returnValues (bool, optional): return matched elements. if false returns indexes of matches Defaults to True.

    Raises:
        ValueError: _description_

    Returns:
        _type_: _description_
    """
    result: dict = None

    if len(array) == 0:
        return result
    if field is not None and not isinstance(array[0], dict):
        raise ValueError(
            "Cannot search by field; list does not contain dict %s", xstr(array)
        )

    if field is None:
        result = {index: x for index, x in enumerate(array) if x == value}
    else:
        result = {index: x for index, x in enumerate(array) if x[field] == value}

    return list(result.values()) if returnValues else list(result.keys())


def flatten(array: list):
    """flatten nested list"""
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
    return (
        (seq[pos : pos + size] for pos in range(0, len(seq), size))
        if returnIterator
        else [seq[pos : pos + size] for pos in range(0, len(seq), size)]
    )


def qw(s, returnTuple=False):
    """
    mimics perl's qw function
    usage: qw('a b c') will yield ['a','b','c']
    returnTuple: return a tuple if true, otherwise return list
    """
    if returnTuple:
        return tuple(s.split())
    else:
        return s.split()


def is_equivalent_list(list1, list2):
    """test if two lists contain the same elements;
    order does not matter"""
    return Counter(list1) == Counter(list2)


def is_overlapping_list(list1, list2):
    """returns True if the intersection of the two lists is True
    i.e., at least one element in list2 is in list1
    """
    return bool(set(list1) & set(list2))


def is_subset(list1, list2):
    """returns True if list1 is a subset of list2
    i.e., all elements in list1 are in list2"""
    return set(list1).issubset(list2)


def alphabetize_string_list(slist):
    """sorts a list of strings alphabetically
    takes a list or a string, but always returns a string
    """
    if isinstance(slist, str):
        return ",".join(sorted(slist.split(",")))
    else:
        return ",".join(sorted(slist))


def list_to_indexed_dict(clist):
    """convert list to hash of value -> index"""
    return OrderedDict(zip(clist, range(1, len(clist) + 1)))


def find_in_list(value: str, arr: List[str], ignoreCase=False):
    """
    wrapper for seeing if a string value is 'in' a list
    allows case insensitive matches

    TODO: return index of match?

    Args:
        value (str): string value to lookup
        arr (List[str]): list of strings
        ignoreCase (bool, optional): flag for case sensitive match. Defaults to False.
    """
    if not ignoreCase:
        return value in arr
    else:
        if value.casefold() in (s.casefold() for s in arr):
            return True
    return False


def list_to_string(arr: list, null_str="NULL", delim=",", quote: bool = False):
    """converts a list to string

    Args:
        arr (list): the list to be converted
        null_str (str, optional): string to use for null/None values. Defaults to "NULL".
        delim (str, optional): delimiter. Defaults to ",".
        quote (bool, optional): enclose each list element in single quotes. Defaults to False.

    Returns:
        the string
    """

    if arr is None or len(arr) == 0:
        return null_str

    if quote:
        return delim.join(["'" + xstr(v, null_str=null_str) + "'" for v in arr])
    return delim.join([xstr(v, null_str=null_str) for v in arr])


def drop_nulls(arr):
    """removes nulls from the list"""
    return list(filter(None, arr))


def get_duplicates(array):
    """get duplicate values in an array"""
    return [k for k, v in Counter(array).items() if v > 1]


def remove_duplicates(array, caseInsensitive: bool = False):
    """remove duplicates from a list by transforming to set and back"""
    if not caseInsensitive:
        return [*set(array)]
    else:
        reference = set()
        unique = []
        for value in array:
            lvalue = value.lower()
            if lvalue not in reference:
                reference.add(lvalue)
                unique.append(value)
        return unique


def array_in_string(value, array):
    """check if any element in the array is the string"""
    for elem in array:
        if elem in value:
            return True
    return False


def sum_arrays(a, b):
    """
    calcs per-element sum of two arrays (lists)
    e.g., list a[1,2] + list b[3,4] --> [3,6]
    """
    return [x + y for x, y in zip(a, b)]


def sum_array_list(arrays):
    """
    calcs per-element sum for a
    list of arrays (lists)
    e.g., [[1,2],[3,4]] --> [3,6]
    """
    return [sum(x) for x in zip(*arrays)]


def average_array_list(arrays):
    """
    calcs per-element average for
    a list of arrays (lists)
    e.g., [[1,2],[3,4]] --> [1.5,3]
    """

    n = len(arrays)
    return [float(x) / float(n) for x in sum_array_list(arrays)]


def cumulative_sum(array: List[Union[int, float]]):
    """calculates the cumulative sum array"""
    nElements = len(array)
    cSum = [sum(array[0:x:1]) for x in range(0, nElements + 1)]
    return cSum[1:]
