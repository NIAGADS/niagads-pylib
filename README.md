# JSON Schemas for validating metadata files accompanying DSS Data Submissions

## Auto-generated documentation from JSON Schema Files

Documentation generation epends on:

* Python 3.10+
* [json-schema-for-humans](https://github.com/coveooss/json-schema-for-humans)

> Developer recommendation: install packages in a Python virtual environment (venv)

```bash
pip install json-schema-for-humans
```

and then generate the documentation as follows:

For `HTML`:

```bash
cd metadata/dss
generate-schema-doc --config template_name=js_offline expand_buttons=true schemas/ docs/
```

For `Markdown`:

```bash
cd metadata/dss
generate-schema-doc --config template_name=md show_toc=true schemas/ docs/
```

## Running the test script

Test scripts are available in the `dss/scripts` directory:

* [metadata_validatory.py](./scripts/metadata_validator.py)

Validation depends on:

* Python 3.10+
* git
* [niagads-pylib](https://github.com/NIAGADS/niagads-pylib)

> Developer recommendation: install `niagads-pylib` in a Python virtual environment (venv)

```bash
pip install git+https://github.com/NIAGADS/niagads-pylib.git
```

For usage information run:

```bash
./scripts/metadata_validatory.py --help
```

## Developer Notes

JSON schema can only validate a single cell or dependencies among cells in a single record, it cannot compare across records.  

### To be accounted for in the Python Validators

#### `sample_info`

* _sample_ids_ must be unique within the `sample_info` file
  * <code style="color : green">**DONE**</code>
  * see [niagads-pylib:BiosourcePropertiesValidator.unique_samples](https://github.com/NIAGADS/niagads-pylib/blob/c2d4edf6af105ad46057e670e86a040953da8f25/niagads/validators/metadata.py#L259C1-L267C20)
  
* _sample_ids_ must be unique for the whole experiment (across all `subject_info` files)
  * <code style="color : green">**DONE**</code>
  * are there cases in which multiple `subject_info` files will be submitted?
  
#### `subject_info`

* _subject_ids_ must be unique within the `subject_info` file
  * <code style="color : green">**DONE**</code>
  * see [niagads-pylib:BiosourcePropertiesValidator.unique_samples](https://github.com/NIAGADS/niagads-pylib/blob/c2d4edf6af105ad46057e670e86a040953da8f25/niagads/validators/metadata.py#L259C1-L267C20)