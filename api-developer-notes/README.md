# API Developer Notes

## Exception Handlers

Located in `components/niagads/open_access_api_exception_handlers`.  The exception handler is defined in a nested `add_*_exception_handler` function that takes the `app` as a parameter.  The `@app.exception_handler` decorator is called inside the wrapper.  These wrapper can be imported into main and called after the `app` is initialized.  See  <https://github.com/fastapi/fastapi/issues/917#issuecomment-578381578>, for details.  

