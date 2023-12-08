''' utilities for manipulating pandas DataFrames '''

from pandas import DataFrame
from pandas.api.types import is_string_dtype
from .sys import warning

def strip(df:DataFrame) -> DataFrame:
    """
    wrapper for trim()
    """
    return trim(df)

    
def trim(df:DataFrame) -> DataFrame:
    """
    trim leading and trailing whitespace from all fields in the data frame
    adapted from final example at: 
    https://www.geeksforgeeks.org/pandas-strip-whitespace-from-entire-dataframe/#

    Args:
        df (DataFrame): pandas data frame to modify
    """
    for col in df.columns:
        warning(df[col])
        if is_string_dtype(df[col].dtype):
            df[col] = df[col].map(str.strip)

    return df 
    