# TODOs

* fix bug w/ALFA loading from dbSNP VCF: wrap in {'ALFA':}.  TODO - patch db

* update schema dataset model to reflect new api model
* replace flat_dump w/context based serialization (will get passed to all children)
* can we move casesensitiveenum to common.types ? circular imports?!

## ETL

### Bugs

* make wrappers for sqlalchemy.exc errors NoResultFound, MultipleResultFound so errors can be handled w/out importing from sqlalchemy?

## OWL ETL

* OBJECT PROPERTIES are not always parsing correctly - see example below where CURIE is extracted incorrectly; problematic example below appears to be UBERON, but appears to affect most ontologies.  Sometimes like this and sometimes missing prefix, e.g., sequence ontology has `so#` prefixed object properties; also affects some ANNOTATION PROPERTIES

```text
source_id ontology_term_id term term_iri entity_type label definition
has_component 162250 has component http://purl.obolibrary.org/obo/RO_0002180 OBJECT_PROPERTY has component w 'has component' p if w 'has part' p and w is such that it can be directly disassembled into into n parts p, p2, p3, ..., pn, where these parts are of similar type.
```

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
