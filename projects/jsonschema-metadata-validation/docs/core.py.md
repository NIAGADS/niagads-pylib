<!-- markdownlint-disable -->

<a href="../../../bases/niagads/validate_metadata/core.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `core.py`
validate_metadata 

This script allows the user validate a sample or file manifest metadata file arranged in tabular format (field names in columns, values in rows) against a JSON-Schema file. Results are piped to STDOUT unless `--log` option is specified. 

This tool accepts tab separated value files (.tab) as well as excel (.xls, .xlsx) files. 

This file can also be imported as a module and contains the following functions / tyes: 

 * MetadataValidatorType - enum of types of expected metadata files  * initialize_validator - returns an initialized BiosourcePropertiesValidator or FileManifestValidator  * get_templated_schema_file - builds schema file name and verifies that file exists  * get_templated_metadata_file - builds metadata file name and verifies that file exists  * run - initializes a validator and runs the validaton 

**Global Variables**
---------------
- **LOG_FORMAT_STR**

---

<a href="../../../bases/niagads/validate_metadata/core.py#L53"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_templated_schema_file`

```python
get_templated_schema_file(dir: str, template: str) → str
```

verify that templated schema file ${schemaDir}/{vType}.json exists 



**Args:**
 
 - <b>`path`</b> (str):  path to directory containing schema file 
 - <b>`template`</b> (str):  template name 



**Raises:**
 
 - <b>`FileExistsError`</b>:  if the schema file does not exist 



**Returns:**
 
 - <b>`str`</b>:  schema file name 


---

<a href="../../../bases/niagads/validate_metadata/core.py#L77"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `get_templated_metadata_file`

```python
get_templated_metadata_file(
    prefix: str,
    template: str,
    extensions: List[str] = ['xlsx', 'xls', 'txt', 'csv', 'tab']
) → str
```

find metadata file based on templated name {prefix}{validator_type}.{ext} 



**Args:**
 
 - <b>`path`</b> (str):  file path; may include prefix/file pattern to match (e.g. /files/study1/experiment1-) 
 - <b>`template`</b> (str):  template name 
 - <b>`extensions`</b> (List[str], optional):  allowable file extensions. Defaults to ["xlsx", "xls", "txt", "csv", "tab"]. 



**Raises:**
 
 - <b>`FileNotFoundError`</b>:  if metadata file does not exist 



**Returns:**
 
 - <b>`str`</b>:  metadata file name 


---

<a href="../../../bases/niagads/validate_metadata/core.py#L107"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

## <kbd>function</kbd> `initialize_validator`

```python
initialize_validator(
    file: str,
    schema: str,
    metadataType: MetadataValidatorType,
    idField: str = None
) → Union[BiosourcePropertiesValidator, FileManifestValidator]
```






---

<a href="../../../bases/niagads/validate_metadata/core.py#L131"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

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






---

## <kbd>class</kbd> `MetadataValidatorType`
Types of tabular metadata files 







---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
