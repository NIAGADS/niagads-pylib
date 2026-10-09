"""numeric
The `numeric` module provides a library of
functions for working with or formatting numbers
"""

from decimal import Decimal


def to_scientific_notation(value, precision: int = 2) -> str:
    """Convert value to scientific notation with maximum of
    precision decimal places, but strip trailing or
    leading (exponent) zeros

    Args:
        value (float, int, str or Decimal): value to be converted
        precision (int, optional): precision. Defaults to 2.

    Returns:
        string: number in scientific notation"""

    formatted = f"{Decimal(value):.{precision}e}"

    mantissa, exponent = formatted.split("e")

    # strip trailing zeros and decimal if trailing after zeros are stripped
    # and then convert exponent to int when reassembling to strip
    # leading zeros e.g. -09 -> -9
    mantissa = mantissa.rstrip("0").rstrip(".")
    return f"{mantissa}e{int(exponent)}"


def to_string_with_commas(value):
    """converts number to string with commas as thousandths separator

    Args:
        value (int, float or string): value to be printed

    Raises:
        ValueError: if the value is non-numeric

    Returns:
        string: number with commas as thousandths separator
    """
    if (
        isinstance(value, float)
        or isinstance(value, int)
        or (isinstance(value, str) and value.isnumeric())
    ):
        return "{:,}".format(value)
    else:
        raise ValueError(value + " is not numeric; cannot add comma separators")
