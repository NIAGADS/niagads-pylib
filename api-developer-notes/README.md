# API Developer Notes

## Dynamic Site configurtion

Checks for an environemntal variable named `SERVICE_ENV`.  If set to `dev` or `development` (case insensitive), tries to load configuration from `dev.env`, if set to `prod` or `production` tries to load configuration from `prod.env`; else looks for a `.env` file.

see [open_access_api_configuration](../components/niagads/open_access_api_configuration/core.py) for implementation.

## Exception Handlers

Located in [open_access_api_handlers](../components/niagads/open_access_api_exception_handlers).  The exception handler is defined in a nested `add_*_exception_handler` function that takes the `app` as a parameter.  The `@app.exception_handler` decorator is called inside the wrapper.  These wrapper can be imported into main and called after the `app` is initialized.  See  <https://github.com/fastapi/fastapi/issues/917#issuecomment-578381578>, for details.  

