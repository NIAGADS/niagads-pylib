# API TODOS

* revisit GenomicRegion -> zero vs one-based especially for variants
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
