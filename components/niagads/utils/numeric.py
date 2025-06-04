"""numeric
The `numeric` module provides a library of 
functions for working with or formatting numbers
"""

def to_sci_notation(value, precision=2):
    """ convert value to scientific notation

    Args:
        value (float, int or str): value to be converted
        precision (int, optional): precision. Defaults to 2.

    Raises:
        ValueError: if value is of type other than float, int or string 
        and if the string is non-numeric and cannot be converted

    Returns:
        string: number in scientific notation
    """
    pattern = '{:. ' + precision + 'e}'
    if isinstance(value, float) or isinstance(value, int) \
        or (isinstance(value, str) and value.isnumeric()):
        return pattern.format(value)
    else:
        raise ValueError(value + " is not numeric; cannot convert to scientific notation")


def to_string_with_commas(value):
    """converts number to string with commas as thousandths separator

    Args:
        value (int, float or string): value to be printed

    Raises:
        ValueError: if the value is non-numeric

    Returns:
        string: number with commas as thousandths separator
    """
    if isinstance(value, float) or isinstance(value, int) \
        or (isinstance(value, str) and value.isnumeric()):
        return ('{:,}'.format(value))
    else:
        raise ValueError(value + " is not numeric; cannot add comma separators")