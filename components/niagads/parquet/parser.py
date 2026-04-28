"""
Generic parquet file parser with support for filtering and iteration.

Provides a ParquetFileParser class for parsing parquet files with optional
column selection, row filtering, and pandas DataFrame conversion capabilities.
"""

from pathlib import Path
from typing import Iterator, Optional

import pandas as pd
import pyarrow.parquet as pq
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
        return self.parse(as_json=False, **kwargs)

    def to_json(self, transpose=False, **kwargs) -> pd.DataFrame:
        """
        Parse alias, to generate json instead of data frame

        Args:
            transpose (optional, bool): transpose dataframe, defaults to False
            **kwargs: Additional arguments to pass to pandas.read_parquet().

        Returns:
            pd.DataFrame: DataFrame containing the parquet data.
        """
        df = self.parse(as_json=False, **kwargs)
        return df.T.to_json() if transpose else df.to_json()

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
            table = pq.read_table(self._file)
            schema = table.schema
            return {field.name: str(field.type) for field in schema}

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

    def unique_values(self, column: str, **kwargs) -> list:
        """
        Extract unique values from a specified column.

        Args:
            column (str): Name of the column to extract unique values from.
            **kwargs: Additional arguments to pass to pandas.read_parquet().

        Returns:
            list: Sorted list of unique values in the column.

        Raises:
            ValueError: If the column does not exist in the parquet file.
            Exception: If there's an error reading the parquet file.
        """
        try:
            if self._verbose:
                self.logger.info(f"Extracting unique values from column: {column}")

            df = self.parse(**kwargs)

            if column not in df.columns:
                raise ValueError(
                    f"Column '{column}' not found in parquet file. "
                    f"Available columns: {list(df.columns)}"
                )

            unique_vals = sorted(df[column].dropna().unique().tolist())

            if self._verbose:
                self.logger.info(
                    f"Found {len(unique_vals)} unique values in column '{column}'"
                )

            return unique_vals

        except ValueError:
            raise
        except Exception as err:
            self.logger.error(
                f"Error extracting unique values from column '{column}' "
                f"in {self._file}: {err}"
            )
            raise

    def column_mapping(
        self,
        key_column: str,
        value_column: str,
        fail_on_duplicates: bool = True,
        **kwargs,
    ) -> dict:
        """
        Generate a mapping between values in two columns.

        Creates a dictionary where keys come from one column and values from another.
        Useful for creating mappings like term -> ontology_term, gene_id -> symbol, etc.

        Handles NA values and duplicates as follows:
        - Skips rows where key_column is NA (keys cannot be NA)
        - Preserves NA values where they appear in value_column
        - For duplicate keys with different values, creates a list of values

        Args:
            key_column (str): Name of the column to use as dictionary keys.
            value_column (str): Name of the column to use as dictionary values.
            fail_on_duplicates (Optional, boolean): fail if key maps to mulitple values. Defaults to True
            **kwargs: Additional arguments to pass to pandas.read_parquet().

        Returns:
            dict: Mapping with values from key_column as keys and value_column as values.
                Values are either scalars or lists (if multiple values map to same key) and fail_on_duplicates = False.

        Raises:
            ValueError: If either column does not exist in the parquet file.
            Exception: If there's an error reading the parquet file.

        Example:
            >>> parser = ParquetFileParser("genes.parquet")
            >>> gene_symbols = parser.column_mapping("ensembl_id", "hgnc_symbol")
            >>> print(gene_symbols["ENSG00000000003"])
            "TANGO1"
        """
        try:
            if self._verbose:
                self.logger.info(f"Creating mapping: {key_column} -> {value_column}")

            df = self.parse(**kwargs)

            # Validate columns exist
            missing_cols = [
                col for col in [key_column, value_column] if col not in df.columns
            ]
            if missing_cols:
                raise ValueError(
                    f"Column(s) {missing_cols} not found in parquet file. "
                    f"Available columns: {list(df.columns)}"
                )

            # Keep only rows where key is not NA (skip NA keys)
            mapping_df = df[[key_column, value_column]].dropna(subset=[key_column])

            # Group by key and collect values (including NAs)
            mapping = {}
            for key, group in mapping_df.groupby(key_column):
                values = group[value_column].tolist()

                # Remove NAs and duplicates
                unique_values = list(set(v for v in values if not pd.isna(v)))

                if len(unique_values) == 0:
                    if self._verbose:
                        self.logger.warning(f"No mappings found for key `{key}")
                    continue

                if len(unique_values) > 1:
                    msg = f"Multiple mappings found for key `{key}`: {unique_values}"
                    if fail_on_duplicates:
                        raise ValueError(msg)
                    if self._verbose:
                        self.logger.warning(msg)
                    mapping[key] = unique_values
                else:
                    mapping[key] = unique_values[0]

            if self._verbose:
                self.logger.info(
                    f"Generated mapping with {len(mapping)} entries "
                    f"from {len(mapping_df)} rows"
                )

            return mapping

        except Exception as err:
            self.logger.error(
                f"Error creating mapping from columns '{key_column}' -> "
                f"'{value_column}' in {self._file}: {err}"
            )
            raise
