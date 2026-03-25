# Writing an ETL Plugin for GenomicsDB

This guide explains how to create a new ETL plugin for the GenomicsDB ETL framework. Plugins orchestrate extract, transform, and load (ETL) operations, and are managed by the pipeline system.

## Required Plugin Methods

All ETL plugins are Python classes that inherit from [`AbstractBasePlugin`](../../../components/niagads/etl/plugins/base.py) and implement its required (abstract) methods.

> **Note:** An abstract class defines methods and properties that must be implemented by subclasses. Abstract methods are placeholders—your plugin must provide concrete implementations for them, or Python will raise an error.

- `extract`: Reads and parses records from your data source. You may yield records one at a time or return a collection, depending on the plugin's load strategy, data size, and data type. Choose the approach that best fits your ETL logic and the requirements of your plugin.
- `transform`: Takes the output from `extract` and applies any necessary data cleaning, normalization, or conversion. Returns the transformed record or collection. Use this to prepare data for loading, such as mapping fields or validating values.
- `load`: Receives transformed records and writes them to the database using the provided async SQLAlchemy session. Handles inserts, updates, or deletes as needed, and returns a `ResumeCheckpoint` object (or None) to support resuming or checkpointing. Use this for all database write operations.
- `get_record_id`: Extracts and returns a unique identifier from a record, which is used for checkpointing and resuming ETL runs. Returns a string or value that uniquely identifies each record (such as a primary key or unique field).

## Optional (async) Lifecycle methods

- `preprocess`: Called in PREPROCESS mode. Override to implement preprocessing logic (e.g., generate intermediate files, validation).
- `on_run_complete`: Called automatically after every run (success or failure). Override to perform custom cleanup, logging, or post-processing.
- `on_run_start`: Called at the start of a run. Override for custom initialization or validation, or one-off database fetches for foreign key links.
- `undo`: Called in `UNDO` mode. Fully implmented in base, but there maybe unique cases where `undo` needs to be customized; override if necessary.

> **Important:**: The default `undo` implementation `DELETES` only! It will not rollback updates.  If your plugin provides updates, you must implement a custom UNDO that at the very least, just provides a warning to the user that UNDO is not possible or conditions deletes based on differences between modification and creation date.

## Plugin Registry and Metadata

All ETL plugins must be registered with the [`PluginRegistry`](../../../components/niagads/etl/plugins/registry.py). The registry is a central catalog that tracks available plugins, their metadata, and their configuration. This enables the pipeline to discover, orchestrate, and manage plugins dynamically, without hardcoding plugin classes or paths. By registering plugins, users can run a plugin or add it to the pipeline simply by specifying its name, without needing to reference its implementation directly.

**Required plugin metadata:**

- `description`: A string describing the plugin's purpose and behavior.
- `parameter_model`: A Pydantic model class for plugin parameters (must subclass `BasePluginParams`).
- `operation`: An `ETLOperation` enum value specifying the plugin's ETL operation type.
- `affected_tables`: A list of SQLAlchemy table classes affected by the plugin. Tables should be listed in cascading dependency order to facilitate `undo` operations (e.g., Pathway, then PathwayMembership)
- `load_strategy`: An `ETLLoadStrategy` enum value (chunked, bulk, batch) specifying how records are loaded. See [Load Strategies](#load-strategies).
- `version`: A string indicating the plugin version.

See [`PluginMetadata`](../../../components/niagads/etl/plugins/metadata.py) for the metadata structure.

An [example plugin](#example-simple-text-loader-plugin) scaffold is provided in this README. Please also refer to existing implementations in `etl/plugins` for reference and inspiration.

---

## Plugin Development Essentials

### Parameter Model

Define a Pydantic model for plugin parameters. Inherit from [`BasePluginParams`](../../../components/niagads/etl/plugins/parameters.py) and add plugin-specific fields.

#### Parameter Validation

Plugin parameter validation is critical for robust ETL operation. There are several ways to validate parameters:

1. **Pydantic out-of-box validation:**
    - All plugin parameter models inherit from Pydantic, which provides automatic type checking, required field enforcement, and value validation. This ensures that parameters are checked for correctness before plugin execution.

2. **Custom Pydantic validators:**
    - You can define custom validation logic in your parameter model using Pydantic's `@field_validator` or `@model_validator` decorators ([see official documentation](https://docs.pydantic.dev/latest/usage/validators/)). This allows you to enforce constraints, check value ranges, or perform complex validation directly in the model definition.

3. **Validator mixins:**
    - Use validator mixins (e.g., `PathValidatorMixin`) to add reusable validation logic for common parameter types, such as file paths or directories. These mixins provide ready-made validators that can be attached to fields in your parameter model.

4. **Database-based validation in `on_run_start`:**
    - For parameters that require validation against the database (such as checking for valid external database references), override the `on_run_start` lifecycle method. Use this method to perform async database lookups or checks before the ETL run begins, raising errors if validation fails.

### Run ID

Each ETL plugin run is assigned a unique `run_id` by the pipeline. This identifier should be attached to every record processed and loaded by your plugin, typically as a field on the SQLAlchemy model (e.g., `record.run_id = self.run_id`). The `run_id` enables traceability, auditing, and rollback of ETL operations, allowing you to identify which records were created or modified during a specific pipeline execution.

> **Always set the `run_id` before submitting records to the database.**  This field is required for all tables that can be loaded using the ETL pipeline.

### Transaction Wrappers

The ETL framework provides transaction wrappers to simplify and standardize database transaction management. These simplify inserts and updates using ORM objects.  They also facilitate assembling linking information by retrieving and updating the ORM with the primary key of the modified record.

- `submit`: Insert the record into the database and return the primary key value.
- `update`: Update the record in the database.

> **NOTE**: These are `async` methods and must be **awaited**.

**Example usage:**

```python
# Transaction Wrappers: Use submit/update methods from TransactionTableMixin
from niagads.database.genomicsdb.schema.reference import OntologyTerm
from niagads.database.genomicsdb.schema.reference import ExternalDatabase

async def load(session, transformed: OntologyTerm):
    externaldb = ExternalDatabase(...) # fill in properties
    external_database_id = await externaldb.submit(session)
    transformed.external_database_id = external_database_id
    await transformed.submit(session)
```

### Lookup Mixins

Lookup mixins are provided to facilitate efficient and reusable lookup operations within plugins. These mixins encapsulate common patterns for querying and mapping data, reducing boilerplate and improving maintainability.  All GenomicsDB table classes inherit from this mixin. Use lookup mixins when you need to fetch or map reference data during ETL processing. See [`mixins.py`](../../../components/niagads/etl/plugins/mixins.py) for available mixins and usage patterns.

The following lookup mixins are provided:

- `record_exists` (class method): Check if a record exists in the table based on filter criteria. Returns `True` if a matching record exists, `False` otherwise.
- `find_primary_key` (class method): Return the primary key value(s) for records matching the filter criteria. Throws `NoResultFound` if no record matches, `MultipleResultsFound` if multiple records match and `allow_multiple` is `False`, `NotImplementedError` if no PK is defined.
- `find_stable_id` (class method): Return the stable identifier value(s) for records matching the filter criteria. Throws `NoResultFound` if no record matches, `MultipleResultsFound` if multiple records match and `allow_multiple` is `False`, `NotImplementedError` if `_stable_id` is not defined.
- `fetch_record` (class method): Return the full record(s) for records matching the filter criteria. Throws `NoResultFound` if no record matches, `MultipleResultsFound` if multiple records match and `allow_multiple` is `False`.
- `exists` (instance method): Check if this instance exists in the table. Optionally match only on stable id. Returns `True` if a matching record exists, `False` otherwise.
- `retrieve_primary_key` (instance method): Set the primary key value of this instance if it exists in the database. Returns `True` if the PK was set, `False` if not found.
  
> **NOTE**: These are `async` methods and must be **awaited**.

All lookup functions take an async session object as the first parameter `session`.  

`filters` defining "filter criteria" are dictionaries mapping column names to values. For example, `{"term_id": 123}` will match records where the `term_id` column equals `123`. You can specify multiple fields for more complex lookups, e.g., `{"gene_symbol": "APOE", "type": "protein_coding"}`.

In addition, the mixin also provides the following helpers:

- `table_name` (class method): Return the fully qualified table name for the model.
- `stable_id_column` (class method): Return the name of the stable identifier column. Throws `NotImplementedError` if not defined.
- `primary_key_column` (class method): Return the name of the primary key column. Throws `NotImplementedError` if not defined or not single-column.

**Example usage:**

> Example assumes `session` exists

```python
# Lookup Wrappers: Use LookupTableMixin methods for existence and PK lookup
from niagads.database.genomicsdb.schema.reference import OntologyTerm

# check if a record matching this term exists using the class method
exists = await OntologyTerm.record_exists(session, {"term": term})
# or from an instantiated record -> note for this to work all required fields would need to be populated, e.g., curie
exists = await OntologyTerm(term=term ,...)

# lookup record and get primary key
pk = await OntologyTerm.find_primary_key(session, {"curie": 'GO:12345'})

# retrieve the full matching record
term: OntologyTerm = await OntologyTerm.fetch_record(session, {"curie": 'GO:12345'})

```

### TableRef (Catalog) Mixinx

Some tables include a generic `table_id`, `row_id` pair (e.g., [Gene.AnnotationEvidence](../../../components/niagads/database/genomicsdb/schema/gene/annotation.py)) that references a specific record in any cataloged table, so that the same reference pattern can work across many tables.  This relies on a table catalog, which is located in the `Admin` schema.  The [Admin.TableCatalog](../../../components/niagads/database/genomicsdb/schema/admin/catalog.py) provides a classmethod `get_table_ref` that takes a table class and returns the table reference in the catalog as [TableRef](../../../components/niagads/database/genomicsdb/schema/admin/types.py) object (providing: schema name and id, table name and id, and the table primary key field)

**Example usage:**

> Example assumes `session` exists

```python
from niagads.database.genomicsdb.schema.reference import OntologyTerm
from niagads.database.genomicsdb.schema.admin.catalog import TableCatalog
from niagads.database.genomicsdb.schema.admin.types import TableRef

my_table_ref: TableRef = TableRef.get_table_ref(session, OntologyTerm)
my_table_id = my_table_ref.table_id
```

see [OntologyTermLoader](./plugins/reference/ontology/owl.py) plugin for full usage example.

### Logging

The base plugin provides automated logging for ETL operations including plugin configuration, warnings, exceptions, and status reporting. Use `self.logger` for custom log messages or to add debug and verbose messaging. All major lifecycle events, errors, and transaction counts are logged automatically to facilitate monitoring and debugging.

### Error Handling

The base plugin handles error logging and propagation for all ETL operations. Custom error handling can be added in your plugin if needed, but most common errors are caught and logged by the base class to ensure consistent reporting and robust pipeline execution.

### Session Usage

The base plugin manages the database connection, passing an SQLAlchemy [AsyncSession](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.AsyncSession) (as `session`) to `load` and the `on_run_start` life cycle function for use.

For most use cases, plugins should not need to create additional connection pools or generate additional session handlers.  However, exceptions do exist and the base plugin provides two methods for accessing or creating a database session if need be.

You only need to use these methods if:

1. You need to access the database outside `load` (e.g., in `preprocess`, initialization, or lifecycle hooks for validation or mapping).
   - Use `self.session_ctx()` to obtain a session from the plugin's pool for single-threaded access.
2. You need parallel or advanced preprocessing requiring a separate connection pool.
   - Use `self.session_manager(pool_size=...)` to create a new pool, then use its `session_ctx()`.

**Examples:**

*Validation or mapping in preprocess/init/hook:*

```python
async with self.session_ctx() as session:
    # perform validation or mapping
```

*Parallel preprocessing or loading:*

```python
manager = self.session_manager(pool_size=2)
async with manager.session_ctx() as session:
    # perform parallel database operations
```

Refer to [`AbstractBasePlugin`](../../../components/niagads/etl/plugins/base.py) for implementation details.

### Transaction Counting

Transaction counting is automated for all ORM-mediated transactions (inserts, updates, deletes) using SQLAlchemy. The plugin base class tracks these operations automatically for accurate status reporting.

If you execute explicit SQL statements or perform operations outside the ORM, use `self.inc_tx_count` to manually increment transaction counts for those statements.

> `self.inc_txt_count` can also be used to manually track `SKIPS`.

### Checkpoints

> **NOTE**: `Resume` handling not yet formalized; currently implemented at plugin level.

A checkpoint is an object that records the current progress of an ETL plugin run, allowing the pipeline to resume from a specific point in the data source if interrupted or rerun. Checkpoints typically include information such as the last processed line number, record identifier, or a snapshot of the last record.

Plugins generate by returning them from the `load` method. The pipeline uses these checkpoints to support resume, recovery, and robust error handling.

See [`ResumeCheckpoint`](../../../components/niagads/etl/plugins/parameters.py) for the checkpoint structure.

## Plugin Execution and Operation Types

### Load Strategies

Plugins must specify a load strategy in their metadata:

- **CHUNKED**: Records are processed and loaded in chunks. The chunk size is determined by the number of records yielded by `extract` and buffered before calling `load()`.
- **BULK**: All records are extracted and transformed, then loaded in a single call to `load()`.
- **BATCH**: Records are bulk extracted and transformed.  The transformed dataset is split into batches of size `commit_after` before loading. Each batch is passed to `load()` in turn.

Refer to [`AbstractBasePlugin`](../../../components/niagads/etl/plugins/base.py) for orchestration details.

### ETL Operations

Plugins must specify the type of ETL operation in their metadata (`operation`). Common values are:

- **INSERT**: Insert new records.
- **UPDATE**: Update existing records.
- **LOAD**: Insert new or update existing records.

### ETL Execution Modes

The ETL framework supports several modes of operation, controlled by the `mode` parameter (see `ETLExecutionMode` in [`components/niagads/etl/types.py`](../../../components/niagads/etl/types.py)).

- **DRY_RUN**: Simulate the run without performing any database writes. Useful for validating `extract` and `transform` logic and for quick checks.
- **RUN**: Execute the full ETL flow and persist changes according to the plugin's commit strategy.
- **UNDO**: Perform the plugin's undo logic to revert a previous run (plugins that support undo should implement this behavior and list tables in cascading order in `affected_tables`).
- **PREPROCESS**: Run only the plugin's `preprocess` step (if implemented) to generate intermediary artifacts, then exit. No database writes occur. Plugins that produce temporary files in this mode should implement `on_run_complete` to clean up.

> **Important:**: there should be no need to run the plugin with `--mode UNDO`.  There is a wrapper option in the plugin runner (`--undo`) that sets the mode to `UNDO` and manages related configuration settings.

---

### Transaction Management

The ETL runner supports both *non-persistent* (test) and *persistent* data loads. By default (no flag) a run is non-persistent: transactions are rolled back at the end so no changes are saved to the database, which is useful for verifying load logic and identify potential errors in data sources.  In general, it is good practice to run each data load in non-commit mode first.

Add the `--commit` option to your command to persist changes to the database; the runner will commit transactions according to the plugin's commit strategy. Use non-persistent runs for validation and `--commit` when you are ready to apply changes.

> **Developer Hint**: If extract and transform stages involve a lot of processing, please consider a preprocess stage for your plugin, to facilitate non-commit load testing.

**Important:** Plugins should never call `commit()` or `rollback()` on the session directly in `load` or load-helper functions. The base plugin handles all transaction management. Use the provided session for database operations within `load()` and rely on the plugin framework to manage commit/rollback behavior.

---

## Example: Simple Text Loader Plugin

Below is a simplified example of a plugin using the current registry and base class.

```python
from niagads.etl.plugins.base import AbstractBasePlugin
from niagads.etl.plugins.metadata import PluginMetadata
from niagads.etl.plugins.parameters import BasePluginParams, PathValidatorMixin
from niagads.etl.plugins.registry import PluginRegistry
from niagads.etl.plugins.types import ETLOperation, ETLLoadStrategy, ResumeCheckpoint
from niagads.database.genomicsdb.schema.toy import ToyTable # made up schema & table for this example
from pydantic import Field

class SimpleTextLoaderParams(BasePluginParams, PathValidatorMixin):
    file: str = Field(..., description="text file to load")

    # add validation check to ensure that the file exists
    validate_file_exists = PathValidatorMixin.validator("file", is_dir=False)

metadata = PluginMetadata(
    version="1.0",
    description="XML Record Loader",
    load_strategy=ETLLoadStrategy.CHUNKED, # yielding row by row (chunk_size = 1)
    operation=ETLOperation.INSERT,
    affected_tables=[ToyTable],  # List of SQLAlchemy table classes
    parameter_model=SimpleTextLoaderParams,
)

@PluginRegistry.register(metadata)
class SimpleTextLoader(AbstractBasePlugin):
    _params: SimpleTextLoaderParams # type annotation

    def extract(self):
        # Parse header and yield each line as a dict mapping header to values
        with open(self._params.file) as f:
            header = next(f).strip().split("\t")  # assumes tab-delimited
            self.logger.debug(f"Parsed header: {header}")

            for line in f:
                fields = line.strip().split("\t")
                yield dict(zip(header, fields)) # yields one record

    def transform(self, record):
        # .> one record -> one record
        # Example: convert all values to uppercase
        transformed_record = ToyTable(**{k: v.upper() for k, v in record.items()})
        transformed_record.run_id = self.run_id # need to add the run id 
        return transformed_record

    async def load(self, transformed, session) -> ResumeCheckpoint:
        """
        Example: pretend to load records into DB. Replace with actual DB logic as needed.
        """
        await transformed.submit(session) # transformed is of type "ToyTable"
        return ResumeCheckpoint(record_id=self.get_record_id(record))

    def get_record_id(self, record):
        # assume data had an id field for demonstration
        return record.id
```

## Running a Plugin

Plugins can be run via the CLI, programmatically, or through the ETL Pipeline Manager.

> **For a plugin to run, it must be added to plugin registry.**

To register a plugin, use the `@PluginRegistry` decorator as illustrated in the [example plugin](#example-simple-text-loader-plugin).

### Plugin Runner: `runpipe-plugin`

`runpipe-plugin` runs a single registered ETL plugin from the command line and automatically exposes that plugin's parameter model as CLI arguments.

Common runner options:

- `--plugin`: plugin name to run
- `--list`: list registered plugins and exit
- `--help`: show runner or plugin-specific help
- `--debug`: enable debug logging
- `--verbose`: enable verbose logging
- `--undo`: run the plugin in `UNDO` mode
- `--run_id`: ETL run ID required with `--undo`

Shared plugin parameters from `BasePluginParams` are also added automatically for every plugin:

- `--mode`: execution mode (`RUN`, `DRY_RUN`, or `PREPROCESS`); defaults to `RUN`
- `--commit`: enable database writes
- `--commit-after`: number of records to buffer per commit
- `--log-path`: log file path or output directory for plugin logs
- `--resume-checkpoint`: resume from a saved line number or record ID
- `--connection-string`: database connection string override
  
#### Plugin Runner Usage

##### Plugin System Environment

Before running plugins outside the project root, you will need to load the shell environment and set some environmental variables.  If you have access to the [ad-genomicsdb-etl-pipeline](https://github.com/NIAGADS/ad-genomicsdb-etl-pipeline) repository, a template `setEnv.bash` script is provided to simplify this for you.  This template sets the core paths used by the ETL workflow (`PROJECT_DIR`, `DATA_DIR`, and `CONFIG_DIR`), provides `DATABASE_URI` for database access, and activates the project virtual environment.

A typical setup looks like:

```bash
export PROJECT_DIR=/path/to/project-root
export DATA_DIR=/path/to/data
export CONFIG_DIR=$PROJECT_DIR/ad-genomicsdb-etl-pipeline/pipeline
export DATABASE_URI=postgresql://<user>:<pwd>@<host>:<port>/<database>
source $PROJECT_DIR/niagads-pylib/.venv/bin/activate
```

If `DATABASE_URI` is not set, plugins may also accept `--connection-string` to override it for a single run.

##### Plugin Runner Usage Examples

Command line usage is illustrated below using the `XMLRecordLoader` plugin:

During plugin development you can test your plugin without configuring the system environment, by running using Poetry.

```bash
poetry run runpipe-plugin XMLRecordLoader --file test.xml --mode DRY_RUN
```

In production, set up your environment as described above.  You should then be able to execute your plugin as follows:

To perform a `DRY_RUN` to test extract and transform:

```bash
runpipe-plugin XMLRecordLoader --file test.xml --mode DRY_RUN
```

To get plugin usage specify the `--help` option:

```bash
runpipe-plugin XMLRecordLoader --help
```

To perform a full `RUN` (extract, transform, load) - default mode is `RUN`, without committing:

```bash
runpipe-plugin XMLRecordLoader --file test.xml
```

To commit changes to the database:

```bash
runpipe-plugin XMLRecordLoader --file test.xml --commit
```

To run in `PREPROCESS` mode, if implemented:

```bash
runpipe-plugin XMLRecordLoader --file test.xml --mode PREPROCESS
```

To run in `UNDO` mode.

```bash
runpipe-plugin XMLRecordLoader --file test.xml --undo --run_id <run_id>
```

> **Note**: `UNDO` requires the specific run to be cleared from the database.  Check log files or query the Admin.ETLRun table to identify.
> **Important**: UNDO deletes, it cannot rollback updates.  Please use with caution if your load involves updates.

For more details, see inline documentation in [`AbstractBasePlugin`](../../../components/niagads/etl/plugins/base.py), [`PluginRegistry`](../../../components/niagads/etl/plugins/registry.py), and existing plugins in [`bases/niagads/genomicsdb_etl/etl/plugins`](../genomicsdb_etl).

## Instructions for AI Assistants Writing Plugins

When assisting in writing an ETL plugin, follow these steps:

1. **Review this README**: Understand the plugin architecture, required methods, metadata, wrappers, and lifecycle hooks before writing code.
2. **Review current implementations**: Examine existing plugins in `bases/niagads/genomicsdb_etl/plugins` to understand patterns, conventions, and how to structure your plugin.
3. **Define the parameter model**: Create a Pydantic class inheriting from `BasePluginParams` with all required plugin parameters and validation.
4. **Implement required methods**: Provide `extract`, `transform`, `load`, and `get_record_id` methods following the patterns in this README.
5. **Create metadata**: Define `PluginMetadata` with description, operation type, affected tables, load strategy, and version.
6. **Register the plugin**: Use `@PluginRegistry.register(metadata)` decorator on the plugin class.
7. **Use provided utilities**: Use transaction wrappers (`submit`, `update`) and lookup mixins for database operations.
8. **Handle run_id**: Ensure all records have `run_id` set before submission.
9. **Add optional lifecycle methods**: Override `preprocess`, `on_run_start`, or `on_run_complete` as needed.
10. **Validate parameters**: Use Pydantic validators, mixins, or database checks in `on_run_start`.
11. **Return checkpoints**: Have `load` return `ResumeCheckpoint` for resume support.
12. **Follow conventions**: Review existing plugins, use async/await patterns, and follow project style guidelines in the copilot-instructions file.
