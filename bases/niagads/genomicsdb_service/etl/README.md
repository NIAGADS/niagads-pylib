# Writing an ETL Plugin for GenomicsDB

This guide explains how to create a new ETL plugin for the GenomicsDB ETL framework. Plugins orchestrate extract, transform, and load (ETL) operations, and are managed by the pipeline system. All plugins must inherit from `AbstractBasePlugin` and implement its required methods.

## Plugin Structure

A plugin is a Python class that inherits from `AbstractBasePlugin`. It must implement the following abstract methods and properties:

- `description`: Returns a string describing the plugin.
- `parameter_model`: Returns a Pydantic model class for plugin parameters (subclass of `BasePluginParams`).
- `operation`: Returns the `ETLOperation` type for the plugin.
- `affected_tables`: Returns a list of database tables (`schema.table` or SQLAlchemy models) affected by the plugin.
- `streaming`: Boolean indicating if the plugin processes records one-by-one (streaming) or in bulk.
- `extract`: Extracts records from the data source.
- `transform`: Transforms extracted data.
- `load`: Asynchronously persists transformed data.
- `get_record_id`: Returns a unique identifier for a record (used for checkpointing).

## Example: SimpleTextLoaderPlugin

Below is a simplified example of how to implement a plugin that loads and processes a plain text file, illustrating the required structure and methods.

```python
from niagads.pipeline.plugins.base import AbstractBasePlugin, BasePluginParams
from niagads.genomicsdb.models.admin.pipeline import ETLOperation
from pydantic import Field

class SimpleTextLoaderParams(BasePluginParams):
    text_path: str = Field(..., description="Path to text file to load")

class SimpleTextLoaderPlugin(AbstractBasePlugin):
    _params: SimpleTextLoaderParams # type annotation

    @classmethod
    def description(cls):
        return "Loads and processes lines from a plain tab-delimited text file."

    @classmethod
    def parameter_model(cls):
        return SimpleTextLoaderParams

    @property
    def operation(self):
        return ETLOperation.INSERT

    @property
    def affected_tables(self):
        return ["genomicsdb.text_table"]

    @property
    def streaming(self):
        return True

    def extract(self):
        # Parse header and yield each line as a dict mapping header to values
        with open(self._params.text_path) as f:
            header = next(f).strip().split("\t")  # assumes tab-delimited
            for line in f:
                fields = line.strip().split("\t")
                yield dict(zip(header, fields))

    def transform(self, data):
        # Example: convert all values to uppercase
        return {k: v.upper() for k, v in data.items()}

    async def load(self, transformed, mode):
        # Example: pretend to load records into DB
        # Replace with actual DB logic as needed
        print(f"Loaded {len(transformed)} records: {transformed}")
        return len(transformed)

    def get_record_id(self, record):
        # assume data had an id field for demonstration
        return record["id"]
```

## Key Points

- **Parameter Model**: Define a Pydantic model for plugin parameters. Inherit from `BasePluginParams` and add any plugin-specific fields.
- **Streaming vs Bulk**: Set the `streaming` property. If `True`, records are processed line by line and loaded in batches; if `False`, the entire dataset is processed at once (bulk).  Loading will still be in batches.
- **ETL Methods**: Implement `extract`, `transform`, and `load` methods. Use `self.__session_manager` for loading data.
- **Checkpointing**: Implement `get_record_id` to support resume and checkpoint features.
- **Logging**: Use `self.logger` for JSON logging and status updates.

## Running a Plugin

Plugins can be run via the CLI, programmatically, or through the ETL Pipeline Mangaer. For CLI usage:

```bash
poetry run gdbpexec-plugin SimpleTextLoaderPlugin --text-path /path/to/file.txt --mode COMMIT
```

To get plugin usage add the `--help` option:

```bash
poetry run gdbpexec-plugin SimpleTextLoaderPlugin --help
```


For more details, see the documentation for `AbstractBasePlugin` and existing plugins in the repository.
