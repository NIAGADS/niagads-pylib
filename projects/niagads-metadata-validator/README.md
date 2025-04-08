<!-- markdownlint-disable -->

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/bases/niagads/metadata_validator_tool/core.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>package</kbd> `NIAGADS: niagads-metadata-validator`
NIAGADS JSON Schema based metadata validation. 

This tool allows the user to perform [JSON Schema](https://json-schema.org/)-based validation of a sample or file manifest metadata file arranged in tabular format (with a header row that has field names matching the validation schema). 

The tool works for delimited text files (.tab, .csv., .txt) as well as excel (.xls, .xlsx) files. 

This tool can be run as a script or can also be imported as a module.  When run as a script, results are piped to STDOUT unless the `--log` option is specified. 

## Requirements

* Python: >3.12,<4.0

---

## Usage

### command-line

Run with the `--help` option to get full USAGE information

```bash
validate-metadata --help
```

### module

Import package into your python script.

```python
import niagads.metadata_validator_tool.core as mv_tool
```

Use [`vm_tool.initialize_validator`](#function-initialize_validator) to initialize and retrieve a validator object for further manipulation. Use [`vm_tool.run`](#function-run) to initialize and run a validation with default configuration. See [validator documentation](https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/README.md) for more information about validator properties and member functions.




Explore example code in a Jupyter notebook, schema, and metadata files in the repository: [nigads-pylib/examples/metadata-validator-test](https://github.com/NIAGADS/niagads-pylib/tree/6b54d6b1b836564e79f5cf40afaf3522c3379732/development/metadata-validator-test).

---

## API Reference

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/bases/niagads/metadata_validator_tool/core.py#L50"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_templated_schema_file`

```python
get_templated_schema_file(dir: str, template: str) → str
```

Verify that templated schema file `{schemaDir}/{vType}.json` exists. 



**Args:**
 
 - <b>`path`</b> (str):  path to directory containing schema file 
 - <b>`template`</b> (str):  template name 



**Raises:**
 
 - <b>`FileExistsError`</b>:  if the schema file does not exist 



**Returns:**
 
 - <b>`str`</b>:  schema file name 


---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/bases/niagads/metadata_validator_tool/core.py#L73"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_templated_metadata_file`

```python
get_templated_metadata_file(
    prefix: str,
    template: str,
    extensions: List[str] = ['xlsx', 'xls', 'txt', 'csv', 'tab']
) → str
```

Find metadata file based on templated name `{prefix}{validator_type}.{ext}`. 



**Args:**
 
 - <b>`path`</b> (str):  file path; may include prefix/file pattern to match (e.g. /files/study1/experiment1-) 
 - <b>`template`</b> (str):  template name 
 - <b>`extensions`</b> (List[str], optional):  allowable file extensions. Defaults to ["xlsx", "xls", "txt", "csv", "tab"]. 



**Raises:**
 
 - <b>`FileNotFoundError`</b>:  if metadata file does not exist 



**Returns:**
 
 - <b>`str`</b>:  metadata file name 


---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/bases/niagads/metadata_validator_tool/core.py#L102"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `initialize_validator`

```python
initialize_validator(
    file: str,
    schema: str,
    metadataType: MetadataValidatorType,
    idField: str = None
) → Union[BiosourcePropertiesValidator, FileManifestValidator]
```

Initialize and return a metadata validator. 



**Args:**
 
 - <b>`file`</b> (str):  metadata file name 
 - <b>`schema`</b> (str):  JSONschema file name 
 - <b>`metadataType`</b> (MetadataValidatorType):  type of metadata to be validated 
 - <b>`idField`</b> (str, optional):  biosource id field in the metadata file; required for `BIOSOURCE_PROPERTIES` validation. Defaults to None. 



**Raises:**
 
 - <b>`RuntimeError`</b>:  if `metadataType == 'BIOSOURCE_PROPERTIES'` and no `idField` was provided 
 - <b>`ValueError`</b>:  if invalid `metadataType` is specified 



**Returns:**
 
 - <b>`Union[BiosourcePropertiesValidator, FileManifestValidator]`</b>:  the validator object 


---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/bases/niagads/metadata_validator_tool/core.py#L140"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `run`

```python
run(
    file: str,
    schema: str,
    metadataType: str,
    idField: str = None,
    failOnError: bool = False
)
```

Run validation. 

Validator initialization fully encapsulated.  Returns validation result. 



**Args:**
 
 - <b>`file`</b> (str):  metadata file name 
 - <b>`schema`</b> (str):  JSONschema file name 
 - <b>`metadataType`</b> (MetadataValidatorType):  type of metadata to be validated 
 - <b>`idField`</b> (str, optional):  biosource id field in the metadata file; required for `BIOSOURCE_PROPERTIES` valdiatoin. Defaults to None. 
 - <b>`failOnError`</b> (bool, optional):  raise an exception on validation error if true, otherwise returns list of validation errors. Defaults to False. 



**Returns:**
 
 - <b>`list`</b>:  list of validation errors 


---

## <kbd>class</kbd> `MetadataValidatorType`
Enum defining types of supported tabular metadata files. 

```python
BIOSOURCE_PROPERTIES = '''biosource properties file;
a file that maps a sample or participant to descriptive properties
(e.g., phenotype or material) or a ISA-TAB-like sample file'''

FILE_MANIFEST = "file manifest or a sample-data-relationship (SDRF) file"
``` 







---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
