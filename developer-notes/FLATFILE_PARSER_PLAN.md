# Flatfile Parser Component Plan

## Goal

Create a lightweight parser-only component for plain text file formats with minimal dependencies.

Recommended package name:

- `niagads.flatfile`

This name fits well for record-oriented text formats such as VCF, GFF3, TSV, BED, and similar line-based or delimited files.

## Scope

This component should provide:

- shared parser base classes
- file iteration helpers
- line preprocessing and skipping behavior
- optional header parsing support
- format-specific subclasses built on top of the shared base

This component should not provide:

- writers
- pandas-heavy helpers in the core base
- format-specific biological logic in the shared base

## Proposed Structure

```text
niagads/
  flatfile/
    __init__.py
    core.py
    delimited.py
```

Possible later format packages:

```text
niagads/
  vcf/
  gff3/
  csv_parser/
```

Or, if you eventually want stronger consolidation:

```text
niagads/
  flatfile/
    core.py
    delimited.py
    vcf.py
    gff3.py
```

## Migration Plan

1. Add `niagads.flatfile.core` with a minimal abstract `FlatfileParser[T]`.
2. Add an optional `TabularTextParser[T]` or `DelimitedParser[T]` layer for header-aware delimited formats.
3. Migrate simple line-based parsers first, especially ones that already work record-by-record.
4. Keep format-specific data models, such as `VCFEntry`, inside their existing domain packages unless a shared model layer becomes clearly useful.
5. Let dependency-heavy helpers remain outside the base layer.
   Example: `cyvcf2`, `pandas`, or parser-specific normalization logic should not live in `flatfile.core`.
6. Update existing parsers incrementally rather than doing a big-bang rename.

## Design Principles

- parser-only, no writers
- dependency-light core
- iterator-first API
- subclasses own format semantics
- easy to reuse in ETL plugins
- safe defaults for text handling

## Example Base Class

```python
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, Iterator, TypeVar

T = TypeVar("T")


class FlatfileParser(ABC, Generic[T]):
    """
    Minimal base class for plain-text record parsers.
    """

    def __init__(self, file: str, *, encoding: str = "utf-8", debug: bool = False):
        self._file = Path(file)
        self._encoding = encoding
        self._debug = debug
        self.logger = logging.getLogger(self.__class__.__module__)

    @property
    def file(self) -> Path:
        return self._file

    def open(self):
        return self._file.open("r", encoding=self._encoding, errors="ignore")

    def preprocess_line(self, line: str) -> str:
        return line.rstrip("\n")

    def is_ignored_line(self, line: str) -> bool:
        return line.strip() == ""

    @abstractmethod
    def parse_line(self, line: str) -> T:
        """
        Parse one non-ignored line into a record.
        """

    def __iter__(self) -> Iterator[T]:
        with self.open() as fh:
            for line_number, raw_line in enumerate(fh, start=1):
                line = self.preprocess_line(raw_line)
                if self.is_ignored_line(line):
                    continue

                try:
                    yield self.parse_line(line)
                except Exception as err:
                    raise ValueError(
                        f"Failed parsing {self.file} at line {line_number}"
                    ) from err
```

## Optional Delimited Layer

This adds common support for formats that use a delimiter and may contain a header row.

```python
from __future__ import annotations

from abc import abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class TabularTextParser(FlatfileParser[T], Generic[T]):
    def __init__(
        self,
        file: str,
        *,
        delimiter: str = "\t",
        encoding: str = "utf-8",
        debug: bool = False,
    ):
        super().__init__(file, encoding=encoding, debug=debug)
        self._delimiter = delimiter
        self._header: list[str] | None = None

    @property
    def header(self) -> list[str] | None:
        return self._header

    def is_header_line(self, line: str) -> bool:
        return False

    def parse_header(self, line: str) -> None:
        self._header = line.lstrip("#").split(self._delimiter)

    @abstractmethod
    def parse_record(self, line: str) -> T:
        pass

    def parse_line(self, line: str) -> T:
        if self.is_header_line(line):
            self.parse_header(line)
            raise SkipLine()
        return self.parse_record(line)

    def __iter__(self):
        with self.open() as fh:
            for line_number, raw_line in enumerate(fh, start=1):
                line = self.preprocess_line(raw_line)
                if self.is_ignored_line(line):
                    continue

                try:
                    record = self.parse_line(line)
                except SkipLine:
                    continue
                except Exception as err:
                    raise ValueError(
                        f"Failed parsing {self.file} at line {line_number}"
                    ) from err

                yield record


class SkipLine(Exception):
    pass
```

## Example VCF-Oriented Subclass

This keeps VCF behavior format-specific instead of pushing it into the shared base.

```python
class VCFRecordParser(TabularTextParser[dict]):
    def is_ignored_line(self, line: str) -> bool:
        return super().is_ignored_line(line) or line.startswith("##")

    def is_header_line(self, line: str) -> bool:
        return line.startswith("#CHROM")

    def parse_record(self, line: str) -> dict:
        if self.header is None:
            raise ValueError("VCF header has not been parsed yet")

        values = line.split("\t")
        return dict(zip([h.lower().replace('#', '') for h in self.header], values))
```

## Notes For Existing Components

- `niagads.vcf.core` should likely continue to own `VCFEntry`.
- `niagads.vcf.parser` can be modernized to sit on top of `FlatfileParser` or `TabularTextParser`.
- `niagads.csv_parser.core` currently mixes parsing with pandas conversion helpers; that likely belongs outside the minimal shared parser base.
- ETL plugins such as GFF3 loaders can benefit from a common iterator contract without inheriting format-specific assumptions.

## Recommendation

Start with:

- `niagads.flatfile.core.FlatfileParser`
- optionally `niagads.flatfile.delimited.TabularTextParser`

Then adapt VCF and GFF3-style parsers to inherit from those classes only where it reduces duplication.
