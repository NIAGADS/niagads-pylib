# JSON Schemas for validating metadata files accompanying DSS Data Submissions

## Auto-generated documentation from JSON Schema Files

To update the end-user documentation from modified JSON Schema files use the [json-schema-for-humans](https://github.com/coveooss/json-schema-for-humans) Python library

```bash
pip install json-schema-for-humans
```

as follows for `HTML`:

```bash
cd metadata/dss
generate-schema-doc --config template_name=js_offline expand_buttons=true schemas/ docs/
```

or in `Markdown` (beta):

```bash
cd metadata/dss
generate-schema-doc --config template_name=md show_toc=true schemas/ docs/
```

## Developer Notes

JSON schema can only validate a single cell or dependencies among cells in a single record, it cannot compare across records.  

### To be accounted for in the Python Validators

#### `sample_info`

* _sample_ids_ must be unique within the `sample_info` file
  * <code style="color : green">**DONE**</code>
  * see [niagads-pylib:BiosourcePropertiesValidator.unique_samples](https://github.com/NIAGADS/niagads-pylib/blob/c2d4edf6af105ad46057e670e86a040953da8f25/niagads/validators/metadata.py#L259C1-L267C20)
  
* _sample_ids_ must be unique for the whole experiment (across all `subject_info` files)
  * are there cases in which multiple `subject_info` files will be submitted?
  
* should we raise warning when `subject_id` is duplicated?

#### `subject_info`

* _subject_ids_ must be unique within the `subject_info` file
  * <code style="color : green">**DONE**</code>
  * see [niagads-pylib:BiosourcePropertiesValidator.unique_samples](https://github.com/NIAGADS/niagads-pylib/blob/c2d4edf6af105ad46057e670e86a040953da8f25/niagads/validators/metadata.py#L259C1-L267C20)