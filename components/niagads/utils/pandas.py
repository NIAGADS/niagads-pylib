"""utilities for cleaning data in pandas DataFrames"""

from pandas import DataFrame

# from pandas.api.types import is_string_dtype


def strip_df(df: DataFrame) -> DataFrame:
    """
    wrapper for trim()
    """
    return trim_df(df)


def __strip_with_check(value: str) -> str:
    """
    tries to strip, catches the error and returns value if failed
    b/c pandas considers both numbers and strings to be "objects"

    Args:
        value (str): _description_

    Returns
        trimmed string value if string else original value
    """
    try:
        return value.strip()
    except TypeError:
        return value
    except AttributeError:
        return value


def trim_df(df: DataFrame) -> DataFrame:
    """
    trim leading and trailing whitespace from all fields in the data frame
    adapted from final example at:
    https://www.geeksforgeeks.org/pandas-strip-whitespace-from-entire-dataframe/#

    Args:
        df (DataFrame): pandas data frame to modify
    """
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(__strip_with_check)

    return df
