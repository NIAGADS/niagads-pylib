"""
Generic parquet file parser with support for filtering and iteration.

Provides a ParquetFileParser class for parsing parquet files with optional
column selection, row filtering, and pandas DataFrame conversion capabilities.
"""

from pathlib import Path
from typing import Optional, Iterator, Any

import pandas as pd

from niagads.common.core import ComponentBaseMixin
from niagads.utils.sys import verify_path


class ParquetFileParser(ComponentBaseMixin):
    """
    Generic parser for parquet files with filtering and iteration support.

    Attributes:
        file (str): Path to the parquet file.
        columns (list[str], optional): Specific columns to parse.
        filters (list, optional): PyArrow filters for row-level filtering.
        debug (bool): Debug mode flag.
        verbose (bool): Verbose mode flag.
    """

    def __init__(
        self,
        file: str,
        columns: Optional[list[str]] = None,
        filters: Optional[list] = None,
        debug: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize ParquetFileParser.

        Args:
            file (str): Path to the parquet file.
            columns (list[str], optional): List of column names to read.
                If None, all columns are read. Defaults to None.
            filters (list, optional): PyArrow filter expressions for row filtering.
                See https://arrow.apache.org/docs/python/parquet.html for filter syntax.
                Defaults to None.
            debug (bool, optional): Enable debug logging. Defaults to False.
            verbose (bool, optional): Enable verbose logging. Defaults to False.

        Raises:
            ValueError: If the parquet file does not exist.
        """
        super().__init__(debug=debug, verbose=verbose)

        if not verify_path(file):
            raise ValueError(f"Cannot read {file} - file does not exist.")

        self._file = file
        self._columns = columns
        self._filters = filters
        self._df: Optional[pd.DataFrame] = None

    @property
    def file(self) -> Path:
        """Get the file path."""
        return Path(self._file)

    @property
    def columns(self) -> Optional[list[str]]:
        """Get the list of columns to read."""
        return self._columns

    @property
    def filters(self) -> Optional[list]:
        """Get the filters applied to row selection."""
        return self._filters

    def parse(self, **kwargs) -> pd.DataFrame:
        """
        Parse the parquet file and return a pandas DataFrame.

        Args:
            **kwargs: Additional arguments to pass to pandas.read_parquet().
                Common options: engine='pyarrow' (default), memory_map=True, etc.

        Returns:
            pd.DataFrame: DataFrame containing the parquet data.
        """
        try:
            if self._verbose:
                self.logger.info(f"Parsing parquet file: {self._file}")
                if self._columns:
                    self.logger.info(f"Columns: {self._columns}")
                if self._filters:
                    self.logger.info(f"Filters: {self._filters}")

            self._df = pd.read_parquet(
                self._file,
                columns=self._columns,
                filters=self._filters,
                **kwargs,
            )

            if self._verbose:
                self.logger.info(
                    f"Successfully parsed {len(self._df)} rows, "
                    f"{len(self._df.columns)} columns"
                )

            return self._df

        except Exception as err:
            self.logger.error(f"Error parsing parquet file {self._file}: {err}")
            raise

    def to_dataframe(self, **kwargs) -> pd.DataFrame:
        """
        Alias for parse() for convenience.

        Args:
            **kwargs: Additional arguments to pass to pandas.read_parquet().

        Returns:
            pd.DataFrame: DataFrame containing the parquet data.
        """
        return self.parse(**kwargs)

    def __iter__(self, **kwargs) -> Iterator[dict]:
        """
        Iterate over rows in the parquet file as dictionaries.

        Args:
            **kwargs: Additional arguments to pass to pandas.read_parquet().

        Yields:
            dict: Each row as a dictionary with column names as keys.
        """
        df = self.parse(**kwargs)
        for _, row in df.iterrows():
            yield row.to_dict()

    def schema(self) -> dict:
        """
        Get the schema of the parquet file.

        Returns:
            dict: Column names mapped to their data types.

        Raises:
            RuntimeError: If parquet file cannot be read.
        """
        try:
            import pyarrow.parquet as pq

            table = pq.read_table(self._file)
            schema = table.schema
            return {field.name: str(field.type) for field in schema}

        except ImportError as err:
            raise RuntimeError(
                "PyArrow is required to read parquet schema. "
                "Install with: pip install pyarrow"
            ) from err
        except Exception as err:
            self.logger.error(f"Error parsing schema from {self._file}: {err}")
            raise

    def row_count(self) -> int:
        """
        Get the number of rows in the parquet file.

        Returns:
            int: Number of rows (optionally filtered based on filters).

        Note:
            If filters are applied, the count reflects the filtered data.
        """
        try:
            import pyarrow.parquet as pq

            table = pq.read_table(self._file, filters=self._filters)
            return len(table)

        except ImportError as err:
            raise RuntimeError(
                "PyArrow is required to get row count. "
                "Install with: pip install pyarrow"
            ) from err
        except Exception as err:
            self.logger.error(f"Error getting row count from {self._file}: {err}")
            raise
