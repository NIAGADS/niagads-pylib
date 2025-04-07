<!-- markdownlint-disable -->

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L0"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

# <kbd>module</kbd> `core.py`






---

## <kbd>class</kbd> `BiosourcePropertiesValidator`
validate biosource properties in a CSV format file, with column names and 1 row per sample or participant 

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L89"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(fileName, schema, debug: bool = False)
```








---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L117"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `get_biosource_ids`

```python
get_biosource_ids()
```

extract biosource IDs 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L98"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `require_unique_identifiers`

```python
require_unique_identifiers()
```





---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L123"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `run`

```python
run(failOnError: bool = False)
```

run validation on each row 

wrapper of TableValidator.riun that also does sample validation 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L94"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `set_biosource_id`

```python
set_biosource_id(idField: str, requireUnique: bool = False)
```





---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L101"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `validate_unqiue_identifiers`

```python
validate_unqiue_identifiers(validationResult: dict, failOnError: bool = False)
```






---

## <kbd>class</kbd> `FileManifestValidator`
validate a file manifest in CSV format, with column names and 1 row per file 

also compares against list of samples / biosources to make sure all biosources are known 

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L17"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `__init__`

```python
__init__(fileName, schema, debug: bool = False)
```








---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L68"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `run`

```python
run(failOnError: bool = False)
```

run validation on each row 

wrapper of TableValidator.run that also does sample validation 

---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L25"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `set_sample_field`

```python
set_sample_field(field: str)
```





---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L22"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `set_sample_reference`

```python
set_sample_reference(sampleReference: List[str])
```





---

<a href="https://github.com/NIAGADS/niagads-pylib/blob/main/components/niagads/metadata_validator/core.py#L28"><img align="right" style="float:right;" src="https://img.shields.io/badge/-source-cccccc?style=flat-square"></a>

### <kbd>function</kbd> `validate_samples`

```python
validate_samples(validationResult: dict, failOnError: bool = False)
```

verifies that samples in the file manifest are present in a reference list of samples 



**Args:**
 
 - <b>`validationResult`</b> (dict):  validation result to be updated 
 - <b>`failOnError`</b> (bool, optional):  fail on error; if False, returns list of errors.  Defaults to False. 



**Returns:**
 updated validation result 




---

_This file was automatically generated via [lazydocs](https://github.com/ml-tooling/lazydocs)._
