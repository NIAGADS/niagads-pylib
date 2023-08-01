""" library of array, list, and set manipulation functions """

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
