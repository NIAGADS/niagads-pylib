# TODOs

* get_field_iri is in a helper, move to an OntologyTerm object/model
* get rid of `TrackDataStore` add `is_filer_track` to track & track collection, exclude from serialization

## API

* Add explicit types for nested dictionaries in API responses, including
  `memberships` and `functional_annotation`, so generated OpenAPI documentation
  describes their structure instead of showing `{"additionalProperty": "anything"}`.

### other

* revisit GenomicRegion -> zero vs one-based for variants
* Pipe SQL Alchemy Echo to log for non-api

```
# --- Logging Configuration ---
sqla_logger = logging.getLogger('sqlalchemy.engine')
sqla_logger.setLevel(logging.INFO) 
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
sqla_logger.addHandler(handler)

# --- SQLAlchemy Usage ---
# Ensure echo=False to avoid duplicate output
engine = create_engine('sqlite:///:memory:', echo=False) 
```
