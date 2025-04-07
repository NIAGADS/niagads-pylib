import logging
import json

from csv import Sniffer, Dialect
from pandas import read_csv, DataFrame

from niagads.dict_utils.core import convert_str2numeric_values
from niagads.pd_dataframe.core import strip


class CSVFileParser:
    """
    parser for CSV files; mainly to add the following functionality:

    * infer delimiter
    * to_json (leveraging pandas)
    """

    def __init__(self, file: str, sep: str = None, debug: bool = False):
        """
        init new CSVParser

        Args:
            file (str): file name (full path)
            sep (str, optional): delimiter; if None will attempt to infer.  Defaults to None.
            debug (bool, optional): enable debug mode. Defaults to False.
        """
        self._debug = debug
        self.logger = logging.getLogger(__name__)
        self.__file = file
        self.__sep = sep
        self.__na = None  # missing value string representation
        self.__strip = False  # flag for trimming leading & trailing whitespace

    def na(self, value: str):
        """
        fill NA's with specified value when using pandas conversions

        Args:
            value (str): value to fill (e.g., 'NULL', 'NA', '.')
        """
        self.__na = value

    def strip(self, strip=True):
        """
        flag indicating whether to iterate over all fields and
        trim leading and trailing spaces when converting to JSON or CSV

        Args:
            strip (bool, optional): trim leading and trailing spaces from all fields. Defaults to True.
        """
        self.__strip = strip

    def to_json(self, transpose=False, returnStr=False, **kwargs):
        """
        converts the CSV file to JSON

        Args:
            transpose (bool, optional): transpose the worksheet?
            returnStr (bool, optional): return jsonStr instead of object
            **kwargs (optional): arguments to pass to `pandas` `read_csv` see
                (see https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html))

        Returns:
            if `returnStr` returns JSON string instead of object
        """

        # orient='records' returns indexes; e.g. [index: {row data}] so need to extract the values
        jsonStr = self.to_pandas_df(transpose, **kwargs).to_json(orient="records")

        # convert strings to numeric so can do typing validation
        jsonObj = json.loads(jsonStr)
        if isinstance(jsonObj, list):
            jsonObj = [convert_str2numeric_values(r) for r in json.loads(jsonStr)]
        else:
            jsonObj = convert_str2numeric_values(jsonObj)

        return json.dumps(jsonObj) if returnStr else json.loads(jsonStr)

    def __trim(self, df: DataFrame):
        """
        trims trailing spaces if set in options

        Args:
            df (DataFrame): pandas data frame
        """
        return strip(df) if self.__strip else df

    def sniff(self):
        """
        'sniff' out / infer the delimitier
        """
        if self.__sep is not None:
            return self.__sep
        else:
            with open(self.__file, "r") as fh:
                dialect: Dialect = Sniffer().sniff(fh.read(1024))
                fh.seek(0)
                return dialect.delimiter

    def to_pandas_df(self, transpose=False, **kwargs) -> DataFrame:
        """
        _summary_

        Args:
            transpose (str): transpose the worksheet
            **kwargs: must match expected args for pandas.read_excel
                (see https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html)

        Returns:
            DataFrame: CSV data in data frame format
        """
        if kwargs is None:
            kwargs = {}

        if "delimiter" not in kwargs:
            kwargs["delimiter"] = self.sniff() if self.__sep is None else self.__sep

        # raise error if False
        df: DataFrame = read_csv(self.__file, **kwargs)
        if self.__na is not None:
            df.fillna(self.__na)
        return self.__trim(df.T) if transpose else self.__trim(df)
