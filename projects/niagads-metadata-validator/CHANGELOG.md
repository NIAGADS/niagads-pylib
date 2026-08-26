# Changelog

All notable changes to the niagads-metadata-validator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.1] - 2026-07-22

### Fixed
- **Validation error handling**: Preserved raw-string validation errors that cannot be decoded as JSON.
- **Validation result structure**: Removed unnecessary nesting from the validation error response.

## [0.3.0] - 2026-07-22

### Added
- **Recurring error promotion**: Added configurable promotion of validation errors that recur across multiple rows.
- **Validation error categorization**: Separated validation errors into file-level, recurring, and row-specific errors.

### Changed
- **Validation result format**: Validation results now return a dictionary containing `file`, `recurring`, and `row_specific` error categories.
- **CSV parsing**: Improved delimiter detection and whitespace handling for delimited metadata files.

## [0.2.3] - 2025-12-08

### Added
- **Case-insensitive validation support**: Added `case_insensitive` parameter to allow case-insensitive matching against JSON schema enums (commits: 390b60dd, 832ee6e5, 550e5f9c)
  - New `--case-insensitive` command-line option in metadata-validator tool
  - Updated `initialize_validator()` and `run()` functions to accept `case_insensitive` parameter
  - Implemented case-insensitive enum validation in JSON validator
  - Added normalization of enum values to match schema-defined case
  - Updated README documentation to reflect new case-insensitive functionality

### Fixed
- **File format error handling**: Improved handling of malformed or invalid input files (commits: b67b3327, eb8a11e6, 598bd069, 6924f30b, 79689733, b7dd5755, df3462a5)
  - Added new `MetadataFileFormatError` exception for file format issues
  - Enhanced Excel parser to catch and report exceptions from invalid file formats
  - Improved CSV parser error handling with better error messages
  - Extended CSV sniffer region to handle files with lengthy data fields

### Changed
- **Python version support**: Relaxed Python version requirement to allow Python 3.10+ (commit: 2cc88ec9)
  - Updated `requires-python` to `>=3.10,<4.0` (previously `>=3.11,<4.0`)
  - Removed `nh3` dependency
- **Dependency updates**: Added `pydantic` (>=2.11.3,<3.0.0) as a project dependency

## [0.2.2] - 2025-04-08

Previous tagged release (tagged as v0.2.2, with version 0.2.0 in pyproject.toml).

## [0.2.0] - Initial Release

Initial release of niagads-metadata-validator.
