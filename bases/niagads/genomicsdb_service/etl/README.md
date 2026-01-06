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

In addition to the required abstract methods and properties, the base plugin provides several properties and hooks that can be optionally overridden to customize plugin behavior:

- **has_preprocess_mode** (property): Return `True` if your plugin supports a preprocessing step (for use with `PREPROCESS` mode). Default is `False`.

- **on_run_complete** (method): Called automatically after every run (success or failure). Override to perform custom cleanup, logging, or post-processing.

These are not required, but can be implemented as needed to extend or customize the plugin lifecycle.

An [example](#example-simpletextloaderplugin) plugin is availble at the end of this README
Explore all implemented plugins in: `bases/niagads/genomicsdb_service/etl/plugin`.

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

---

## Load Strategies

Plugins must specify a load strategy by implementing the `load_strategy` property and returning a value from the `LoadStrategy` enum:

- **CHUNKED**: Records are processed and loaded in chunks, where the chunk size is determined by the plugin developer by number of records yielded by `extract` (and by extension, `transform`). The plugin controls how many records are buffered before calling `load()` based on the `commit_after`parameter value. This is ideal for streaming or line-by-line processing, and allows for flexible chunk sizes based on the data source or transformation logic.

- **BULK**: All records are extracted and transformed, then loaded in a single call to `load()`. The entire dataset is passed at once, and the plugin is responsible for handling all records in one transaction. Use this for small datasets or when batch processing is not required.  

- **BATCH**: The transformed dataset is split into batches of size `commit_after` before loading. Each batch is passed to `load()` in turn. This is useful for large datasets that should be processed in manageable batches, with regular commits and checkpointing.

Select the strategy that best matches your data source and processing requirements. Refer to the `AbstractBasePlugin` documentation and example plugins for implementation details.

---

## ETL Operations

Plugins must specify the type of ETL operation they perform by implementing the `operation` property and returning an `ETLOperation` enum value. Common operations include:

- **INSERT**: Insert new records into the database.
- **UPDATE**: Update existing records.
- **LOAD**: Insert new or update existing records (combined load operation).
- **PATCH**: Partially update records.
- **DELETE**: Delete records.

Use the appropriate operation for your plugin, and always update transaction counts using `self.update_transaction_count()` in your `load()` method for accurate status reporting.

---

## ETL Modes

The ETL framework supports several modes of operation, controlled by the `mode` command line argument (see `ETLMode`):

- **DRY_RUN**: No database writes are performed. The pipeline counts records and simulates processing. Use this for testing and validation of `extract` and `transform` steps.
- **COMMIT**: Records are written to the database. The pipeline commits transactions according to the plugin's logic and the `commit_after` parameter.
- **NON_COMMIT**: Records are processed and written, but the transaction is rolled back at the end. Useful for testing full pipeline execution without persisting changes.
- **PREPROCESS**: (Optional) If the plugin supports it, a preprocessing step can be run before the main ETL. Implement the `has_preprocess_mode` property and logic as needed.

**Important:** Plugins should never call `commit()` or `rollback()` on the session directly. The base plugin handles all transaction management. Only use the provided session for database operations within `load()`.

### PREPROCESS Mode

Use this for workflows that require a preparatory step, such as generating intermediate files or performing expensive validation before loading data.

If `has_preprocess_mode` is `True` and the ETL mode is set to `PREPROCESS`, the pipeline will call your plugin's `extract()` and `transform()` methods, but will not proceed to `load()`. This allows plugins to perform data preparation, validation, or intermediary file generation before the main ETL run.

If `has_preprocess_mode` is not implemented or returns `False`, attempting to run in `PREPROCESS` mode will raise an error.

> Plugins with a preprocess mode should override `on_run_complete` to clean up intermediary files.  This can be made dependent on a plugin parameter.

#### Example Preprocessing Workflow

Suppose you have a plugin that processes a large, messy raw data file and writes a cleaned, intermediate file for efficient loading. The ETL process would look like this:

1. **Preprocess Mode** (first run):
    - **raw data** → `extract()` → `transform()` → **write processed data to intermediate file**
    - No database writes occur; only data preparation and validation are performed.

2. **Commit/Non-Commit Mode** (second run):
    - **processed/intermediate data** → `extract()` → `transform()` → `load()`
    - The plugin reads the preprocessed data, transforms it as needed, and loads it into the database (or simulates loading in DRY_RUN/NON_COMMIT).  

This two-stage approach is useful for workflows where data must be cleaned, normalized, or validated before loading, or when the initial data source is too large or complex to process in a single ETL run.

---

## Example: SimpleTextLoaderPlugin

Below is a simplified example of how to implement a plugin that loads and processes a plain text file, illustrating the required structure and methods.

```python
from niagads.etl.plugins.base import AbstractBasePlugin, LoadStrategy
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin, ResumeCheckpoint
from niagads.genomicsdb.models.admin.pipeline import ETLOperation
from pydantic import Field

class SimpleTextLoaderParams(BasePluginParams, PathValidatorMixin):
    file: str = Field(..., description="text file to load")

    # add validation check to ensure that the file exists
    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)

# register the plugin
@PluginRegistry.register(metadata={"version": 1.0})
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

## Running a Plugin

Plugins can be run via the CLI, programmatically, or through the ETL Pipeline Manager.

> **For a plugin to run, it must be added to plugin registry.**

To register a plugin, use the `@PluginRegistry` decorator as illustrated in the [example plugin](#example-simpletextloaderplugin).

Command line usage is illustrated below using the `XMLRecordLoader` plugin:

From within the project (or root `niagads-pylib` directory):

```bash
poetry run runpipe-plugin XMLRecordLoader --file test.xml --mode DRY_RUN
```

To run outside the project, simply activate the project virtual environment.  First find the path to the virtual environment by executing:

```bash
poetry env activate
```

This will display the command to activate the environment, copy that command and run it. e.g.,

```bash
source /projects/genomicsdb/niagads-pylib/.venv/bin/activate
```

> Do not copy and run the above statement, the path will vary depending on your local directory structure.

You should then be able to execute the plugin runner script directly, as follows:

```bash
runpipe-plugin XMLRecordLoader --file test.xml --mode DRY_RUN
```

To get plugin usage specify the `--help` option:

```bash
runpipe-plugin XMLRecordLoader --help
```

For more details, see the documentation for `AbstractBasePlugin` and existing plugins in the repository at `bases/niagads/genomicsdb_service/etl/plugins`.
