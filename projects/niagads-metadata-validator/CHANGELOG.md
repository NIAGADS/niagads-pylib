# Changelog

All notable changes to the niagads-metadata-validator project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - Better exception handling for abstract method implementation errors (commit: 9bcfdf88)

### Changed
- **Python version support**: Relaxed Python version requirement to allow Python 3.10+ (commit: 2cc88ec9)
  - Updated `requires-python` to `>=3.10,<4.0` (previously `>=3.11,<4.0`)
  - Removed `nh3` dependency
- **Documentation improvements**: Updated README files with enhanced usage instructions and API documentation (commits: 7f193e56, 550e5f9c)
- **Dependency updates**: Added `pydantic` (>=2.11.3,<3.0.0) as a project dependency
- **Code refactoring**: Various internal improvements (commits: 750cc27b, c12dea26, 2a43ae36)
  - Cleaned up TOML configurations
  - Linked utilities in a single component
  - Consolidated common functionality

### Internal
- Added main function improvements (commit: b41a1ed3)
- Code formatting improvements (commit: c2bcf8a3)
- Exception handler enhancements (commit: 5fd415d8)
- Brought in API dependencies (commit: 8eb33efd)
- Various incremental improvements to error messages and validation logic

## [0.2.0] - Earlier Release

Initial tagged release of niagads-metadata-validator.
