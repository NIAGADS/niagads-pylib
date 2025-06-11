# For developers

## Version management

look into: <https://python-semantic-release.readthedocs.io/en/latest/>

## API Developer Notes

### Dynamic Site configurtion

Checks for an environemntal variable named `SERVICE_ENV`.  If set to `dev` or `development` (case insensitive), tries to load configuration from `dev.env`, if set to `prod` or `production` tries to load configuration from `prod.env`; else looks for a `.env` file.

see [open_access_api_configuration](../components/niagads/open_access_api_configuration/core.py) for implementation.

### Exception Handlers

Located in [open_access_api_handlers](../components/niagads/open_access_api_exception_handlers).  The exception handler is defined in a nested `add_*_exception_handler` function that takes the `app` as a parameter.  The `@app.exception_handler` decorator is called inside the wrapper.  These wrapper can be imported into main and called after the `app` is initialized.  See  <https://github.com/fastapi/fastapi/issues/917#issuecomment-578381578>, for details.  

### Abandon SQLModel and use just SQLAlchemy

* use Pydantic models to define JSONB fields <https://github.com/wonderbeyond/SQLAlchemy-Nested-Mutable>
  * based on <https://gist.github.com/imankulov/4051b7805ad737ace7d8de3d3f934d6b> 

* so we can bring in Alembic for versioning
* b/c SQLModel can't handle complexity in inserts; this way we can use the same models in db creation and data loading
* not using SQLModel for GenomicsDB
* hopefully resolve issue w/different types of responses from queries against the databases

* also b/c we are using the table models for db loading scripts and not just FASTApi -> let's separate response serialization from querying

> see great blog post: <https://medium.com/@tclaitken/setting-up-a-fastapi-app-with-async-sqlalchemy-2-0-pydantic-v2-e6c540be4308>

* helpful Alembic example: <https://qiuhongyuan.medium.com/create-a-simple-table-using-sqlalchemy-and-enable-autogeneration-by-alembic-d31623220d84>

#### for future GenomicsDB refactor 

> TODO: move to correct README

* ltrees & sqlalchemy: <https://github.com/kvesteri/sqlalchemy-utils/blob/master/sqlalchemy_utils/types/ltree.py>