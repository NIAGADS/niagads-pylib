# Writing an ETL Plugin for GenomicsDB

This guide explains how to create a new ETL plugin for the GenomicsDB ETL framework. Plugins orchestrate extract, transform, and load (ETL) operations, and are managed by the pipeline system. All plugins must inherit from `AbstractBasePlugin` and implement its required (abstract) methods.

## Plugin Structure

A _plugin_ is a Python class that inherits from `AbstractBasePlugin`. It must implement the following abstract methods and properties:

- `description` (classmethod): Returns a string describing the plugin.
- `parameter_model` (classmethod): Returns a Pydantic model class for plugin parameters (subclass of `BasePluginParams`).
- `operation` (property): Returns the `ETLOperation` type for the plugin.
- `affected_tables` (property): Returns a list of database tables (`schema.table`) affected by the plugin.
- `load_strategy` (property): Returns a `LoadStrategy` enum value indicating chunked, bulk, or batch loading.
- `extract` (method): Extracts records from the data source.
- `transform` (method): Transforms extracted data.
- `load` (async method): Asynchronously loads transformed data into the database.
- `get_record_id` (method): Returns a unique identifier for a record.

## Example: SimpleTextLoaderPlugin

Below is a simplified example of how to implement a plugin that loads and processes a plain text file, illustrating the required structure and methods.

```python
from niagads.etl.plugins.base import AbstractBasePlugin, LoadStrategy
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin, ResumeCheckpoint
from niagads.genomicsdb.models.admin.pipeline import ETLOperation
from pydantic import Field

class SimpleTextLoaderParams(BasePluginParams, PathValidatorMixin):
    file: str = Field(..., description="text file to load")

    # add validation check to ensure that the file passed to the `file`
    # parameter exists
    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)

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
    def load_strategy(self):
        # Use chunked loading for line-by-line processing
        return LoadStrategy.CHUNKED

    def extract(self):
        # Parse header and yield each line as a dict mapping header to values
        with open(self._params.file) as f:
            header = next(f).strip().split("\t")  # assumes tab-delimited
            self.logger.debug(f"Parsed header: {header}")

            for line in f:
                fields = line.strip().split("\t")
                yield dict(zip(header, fields))

    def transform(self, data):
        # Example: convert all values to uppercase
        return {k: v.upper() for k, v in data.items()}

    async def load(self, transformed, session) -> ResumeCheckpoint:
        """
        Example: pretend to load records into DB. Replace with actual DB logic as needed.
        """

        # Simulate DB insert
        self.logger.info(f"Loaded {len(transformed)} records into {self.affected_tables[0]}")

        # Update transaction counts for plugin status logging
        self.update_transaction_count(ETLOperation.INSERT, table_name, len(transformed))

        # Return a checkpoint for resume support
        return self.generate_checkpoint(line=None, record=transformed[-1])
 

    def get_record_id(self, record):
        # assume data had an id field for demonstration
        return record["id"]
```

## Load Strategies

Plugins must specify a load strategy by implementing the `load_strategy` property and returning a value from the `LoadStrategy` enum:

- **CHUNKED**: Records are processed and loaded in chunks, where the chunk size is determined by the plugin developer by number of records yielded by `extract` (and by extension, `transform`). The plugin controls how many records are buffered before calling `load()` based on the `commit_after`parameter value. This is ideal for streaming or line-by-line processing, and allows for flexible chunk sizes based on the data source or transformation logic.

- **BULK**: All records are extracted and transformed, then loaded in a single call to `load()`. The entire dataset is passed at once, and the plugin is responsible for handling all records in one transaction. Use this for small datasets or when batch processing is not required.  

- **BATCH**: The transformed dataset is split into batches of size `commit_after` before loading. Each batch is passed to `load()` in turn. This is useful for large datasets that should be processed in manageable batches, with regular commits and checkpointing.

Select the strategy that best matches your data source and processing requirements. Refer to the `AbstractBasePlugin` documentation and example plugins for implementation details.

---

## Key Points

 **Parameter Model**: Define a Pydantic model for plugin parameters. Inherit from `BasePluginParams` and add any plugin-specific fields. Validation can be handled directly by the Pydantic model.
 **Load Strategy**: Implement the `load_strategy` property to specify chunked, bulk, or batch loading using the `LoadStrategy` enum.
 **ETL Methods**: Implement `extract`, `transform`, and `load` methods. The `load` method must be async and accept both transformed data and a database session.
 **Transaction Counting**: Use `self.update_transaction_count` in `load` to tally inserts, updates, and skips for accurate status reporting.
 **Checkpointing**: Implement `get_record_id` to support resume and checkpoint features. The `load` method should return a `ResumeCheckpoint` object.
 **Session Usage**: Use the provided async SQLAlchemy session in `load` for all database operations. Do not create your own session.
 **Logging**: Use `self.logger` for JSON logging, debug statements, and status updates.
 **Error Handling**: The base plugin handles error logging and propagation; you do not need to wrap ETL methods in try/except unless you need custom error handling.

See the `XMLRecordLoader` for an example of how to write a plugin, including logging and error handling.

## Running a Plugin

Plugins can be run via the CLI, programmatically, or through the ETL Pipeline Manager. Command line usage is illustrated below using the `XMLRecordLoader` plugin:

From within the project (e.g. during development):

```bash
poetry run runpipe-plugin XMLRecordLoader --file test.xml --mode DRY_RUN
```

From outside the project by activating the virtual environment.  First find the path to the virtual environment by executing:

```bash
poetry env activate
```

This will display the command to activate the environment, copy that command and run it. e.g.,

```bash
source /projects/genomicsdb/niagads-pylib/.venv/bin/activate
```

You should then be able to execute the plugin runner without having to call `poetry run`, e.g.,

```bash
runpipe-plugin XMLRecordLoader --file test.xml --mode DRY_RUN
```

To get plugin usage add the `--help` option:

```bash
runpipe-plugin XMLRecordLoader --help
```

For more details, see the documentation for `AbstractBasePlugin` and existing plugins in the repository at `bases/niagads/genomicsdb/etl/plugins`.
