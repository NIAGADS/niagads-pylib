from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator

from niagads.common.core import ComponentBaseMixin
from niagads.utils.sys import is_binary_file, read_open_ctx, verify_path


class AbstractFlatfileParser(ABC, ComponentBaseMixin):
    """
    Minimal base class for plain-text record parsers.

    Subclasses define:
    - how to recognize ignorable lines
    - how to parse one logical record
    """

    def __init__(
        self,
        file: str,
        *,
        encoding: str = "utf-8",
        logger=None,
        debug: bool = False,
        verbose: bool = False,
    ):
        super().__init__(
            debug=debug, verbose=verbose, initialize_logger=logger is not None
        )
        if logger is not None:
            self.logger = logger

        if not verify_path(file):
            raise ValueError(f"Cannot parse {file} - file does not exist.")
        self._file = file
        self._encoding = encoding

    @property
    def file(self) -> Path:
        return self._file

    def open_ctx(self):
        return read_open_ctx(self._file, encoding=self._encoding, is_binary=False)

    def is_ignored_line(self, line: str, line_number: int) -> bool:
        stripped = line.strip()
        return stripped == ""

    def preprocess_line(self, line: str) -> str:
        return line.rstrip()

    @abstractmethod
    def parse_line(self, line: str):
        """Parse one non-ignored line into a record."""

    def __iter__(self) -> Iterator:
        with self.open_ctx() as fh:
            for line_number, raw_line in enumerate(fh, start=1):
                line = self.preprocess_line(raw_line)
                if self.is_ignored_line(line, line_number):
                    continue
                try:
                    yield self.parse_line(line)
                except Exception as err:
                    raise ValueError(
                        f"Failed parsing {self.file} at line {line_number}"
                    ) from err
