# TODOs

## OWL ETL

* add flag to include objectproperties (e.g., for loading the relation ontology)
* resolve annotationproperties by skipping those not in the property iris
* move term_category to triple
* duplicates
* placeholders

 
## Top Priority

The `GeneFeature` model needs to be moved to common.models and out of the API common:

* <https://vscode.dev/github/NIAGADS/niagads-pylib/blob/develop/gene/components/niagads/api_common/models/features/gene.py#L13>

## Better VSCode

* Code Actions (e.g., for abstract classes)
* isort

## Documentation

* use lazydocs instead of sphinx
  
## Developer notes

* settings/configuration for `_api` bases; see <https://docs.pydantic.dev/latest/concepts/pydantic_settings/#usage>
* microservices w/FastAPI - <https://dev.to/paurakhsharma/microservice-in-python-using-fastapi-24cc#using-nginx>