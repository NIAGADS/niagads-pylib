def start_local_for_repl_driven_development_with_jupyter_kernel():
    """Dev-only FastAPI startup.
    Important: only for REPL Driven Development using Jupyter kernel.

    This will start the app in an event loop. This is useful
    when running the app in a Jupyter kernel and connecting clients
    to the kernel.
    """

    import asyncio

    from niagads.open_access_root_api import core
    from uvicorn import Config, Server

    config = Config(core.app, host="127.0.0.1", port=8000)
    server = Server(config)

    loop = asyncio.get_running_loop()

    loop.create_task(server.serve())
