"""
This module provides a CSVFileParser class for parsing CSV files with additional functionality.

The CSVFileParser inherits from AbstractFlatfileParser and provides methods to infer delimiters,
convert CSV data to pandas data frame or JSON, and parse lines into records. The iterator behavior
is inherited from the parent class and utilizes the `parse_line` method to determine the output.

Iterator Behavior:
- With a header: Each iteration returns a dictionary where keys are column names and
    values are the corresponding data.
- Without a header: Each iteration returns a list of values.

Iterator Usage Example:

```python
from niagads.csv_parser.core import CSVFileParser

parser = CSVFileParser("example.csv", header=True)
for record in parser:
    print(record)
```
"""

import json

from csv import Sniffer, Dialect, Error as CSVError
from niagads.exceptions.core import FileFormatError
from niagads.flatfile.base import AbstractFlatfileParser
from pandas import read_csv, DataFrame

from niagads.utils.dict import convert_str2numeric_values
from niagads.utils.pandas import strip_df


class CSVFileParser(AbstractFlatfileParser):
    """
    Parser for CSV files with additional functionality:

    - Infer delimiter automatically.
    - Convert CSV data to JSON using pandas.

    Attributes:
        file (str): Path to the CSV file.
        header (bool): Indicates if the file contains a header row.
        delimiter (str): Delimiter used in the CSV file. If None, it will be inferred.
        encoding (str): File encoding. Defaults to "utf-8".
        debug (bool): Debug mode flag.
        verbose (bool): Verbose mode flag.
    """

    def __init__(
        self,
        file: str,
        header: bool = True,
        delimiter: str = None,
        encoding="ut-f8",
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(file, encoding=encoding, debug=debug, verbose=verbose)

        self.__delimiter = delimiter
        self.__na = None  # missing value string representation
        self.__header = header  # flag indicating whether file has a header
        self.__header_fields = None

    def na(self, value: str):
        """
        Fill NA values with the specified value when using pandas conversions.

        Args:
            value (str): Value to fill (e.g., 'NULL', 'NA', '.').
        """
        self.__na = value

    def to_json(self, transpose=False, return_str=False, **kwargs):
        """
        Convert the CSV file to JSON format.

        Args:
            transpose (bool, optional): Whether to transpose the worksheet. Defaults to False.
            return_str (bool, optional): Whether to return a JSON string instead of an object. Defaults to False.
            **kwargs (optional): arguments to pass to `pandas` `read_csv` see
                (see https://pandas.pydata.org/docs/reference/api/pandas.read_excel.html))

        Returns:
            str or dict: JSON string if `return_str` is True, otherwise a JSON object.
        """

        # orient='records' returns indexes; e.g. [index: {row data}] so need to extract the values
        jsonStr = self.to_pandas_df(transpose, **kwargs).to_json(orient="records")

        # convert strings to numeric so can do typing validation
        jsonObj = json.loads(jsonStr)
        if isinstance(jsonObj, list):
            jsonObj = [convert_str2numeric_values(r) for r in json.loads(jsonStr)]
        else:
            jsonObj = convert_str2numeric_values(jsonObj)

        return json.dumps(jsonObj) if return_str else json.loads(jsonStr)

    def sniff(self, bytes: int = 1024):
        """
        Infer the delimiter used in the CSV file by analyzing its content.

        Args:
            bytes (int, optional): Number of bytes to read for delimiter inference. Defaults to 1024.

        Returns:
            str: Inferred delimiter.

        Raises:
            FileFormatError: If the delimiter cannot be determined.
        """
        try:
            if self.__delimiter is None:
                with self.open_ctx() as fh:
                    dialect: Dialect = Sniffer().sniff(fh.read(bytes))
                    fh.seek(0)
                    self.__delimiter = dialect.delimiter
                return self.__delimiter
        except CSVError as err:
            if bytes < 4096:  # try a larger section of the file
                return self.sniff(bytes=4096)
            raise FileFormatError(
                "Unable to determine file delimiter."
                "File may have inconsistent numbers of columns, sparse data, "
                "or use inconsistent or non-standard delimiters. "
            ) from err

    def to_pandas_df(self, transpose=False, **kwargs) -> DataFrame:
        """
        Convert the CSV file to a pandas DataFrame.

        Args:
            transpose (bool, optional): Whether to transpose the worksheet. Defaults to False.
            **kwargs: Additional arguments passed to pandas `read_csv`.

        Returns:
            DataFrame: CSV data in DataFrame format.
        """
        if kwargs is None:
            kwargs = {}

        if "delimiter" not in kwargs:
            kwargs["delimiter"] = self.sniff()

        if "header" not in kwargs:
            if self.__header is None:
                kwargs["header"] = None
            else:
                kwargs["header"] = 0

        # raise error if False
        df: DataFrame = read_csv(self._file, **kwargs)
        if self.__na is not None:
            df.fillna(self.__na)
        return strip_df(df.T) if transpose else strip_df(df)

    # abstract base class overrides
    def is_ignored_line(self, line: str, line_number: int) -> bool:
        if self.__header and line_number == 1:
            self.__header_fields = line.split(self.sniff())
            return True
        stripped = line.strip()
        return stripped == ""

    def parse_line(self, line: str):
        """Parse one non-ignored line into a record."""
        values = [v.strip() for v in line.split(self.sniff())]
        if self.__header:
            return dict(zip(self.__header_fields, values))
        else:
            return values
