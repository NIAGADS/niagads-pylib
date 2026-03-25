import asyncio
import inspect
import logging
from functools import wraps
from time import perf_counter
from typing import Any

from typing_extensions import deprecated

LOG_FORMAT_STR: str = "%(asctime)s %(levelname)-8s %(message)s"


class FunctionContextLoggerWrapper:
    """
    Wrap any logger-like object and prefix log messages with calling class.function:lineno.
    Delegates all other attributes/methods to the wrapped logger (including custom methods).
    Intercepts all callable methods and prefixes the first argument (if string) with context.
    """

    def __init__(self, logger: Any):
        object.__setattr__(self, "_logger", logger)

    def _get_calling_context(self) -> str:
        stack = inspect.stack()
        try:
            for frame_info in stack[1:]:
                mod = frame_info.frame.f_globals.get("__name__")
                if mod is None:
                    continue
                if mod == __name__ or mod.startswith("logging"):
                    continue
                frame = frame_info.frame
                func = frame.f_code.co_name

                # Skip intermediate logger facade/wrapper methods so we report
                # the application caller rather than helper logger methods.
                if frame.f_locals and "self" in frame.f_locals:
                    try:
                        caller_self = frame.f_locals["self"]
                        cls_name = caller_self.__class__.__name__
                        if (
                            func
                            in {
                                "debug",
                                "info",
                                "warning",
                                "error",
                                "exception",
                                "critical",
                                "log",
                            }
                            and cls_name.endswith(
                                ("Logger", "Wrapper", "Adapter", "Handler")
                            )
                        ):
                            continue
                    except Exception:
                        pass

                lineno = frame.f_lineno
                cls = None
                if frame.f_locals and "self" in frame.f_locals:
                    try:
                        cls = frame.f_locals["self"].__class__.__name__
                    except Exception:
                        cls = None
                prefix = f"{cls + '.' if cls else ''}{func}:{lineno}\t"
                return prefix
        finally:
            for f in stack:
                del f
        return "<unknown>:0 "

    def __getattr__(self, name: str):
        attr = getattr(self._logger, name)
        if callable(attr):

            def wrapper(*args, **kwargs):
                if args and isinstance(args[0], str):
                    prefix = self._get_calling_context()
                    args = (prefix + args[0],) + args[1:]
                return attr(*args, **kwargs)

            wrapper.__name__ = name
            wrapper.__doc__ = attr.__doc__
            return wrapper
        return attr

    def __setattr__(self, name: str, value: Any):
        if name == "_logger":
            return object.__setattr__(self, name, value)
        if hasattr(self._logger, name):
            setattr(self._logger, name, value)
            return
        object.__setattr__(self, name, value)


@deprecated("use the FunctionContextLoggerWrapper instead")
class FunctionContextAdapter(logging.LoggerAdapter):
    """
    A logging adapter that adds the wrapper class name
    (e.g., niagads.utils.logging) to log messages.
    """

    def process(self, msg, kwargs):
        """
        Process the log message to include the full package name in dot notation.
        """
        # Use inspect to get the caller's frame and extract the module/package name
        # current frame is the logger, so need to go up a level
        frame = inspect.getouterframes(inspect.currentframe())[1].frame.f_back.f_back

        """ # full pacakge in dot notation; keep for reference in case want it back
        # i.e., maybe possible for printing lineno etc when debug only
        module = inspect.getmodule(frame)
        if module and module.__name__:
            package = f"{module.__name__}:"  # Full package name in dot notation
        else:
            package = ""
            
        # line number
        lineno = frame.f_lineno
        """

        # FIXME: might need a null or empty check
        if frame.f_locals and "self" in frame.f_locals:
            className = f"{frame.f_locals['self'].__class__.__name__}:"
        else:
            className = ""

        function = frame.f_code.co_name

        return f"{className}{function:<20} {msg}", kwargs


class ExitOnExceptionHandler(logging.Handler):
    """Logging exception handler that catches ERRORS and CRITICAL
    level logging and exits.
    Logs to a file or stderr based on configuration.
    see https://stackoverflow.com/a/48201163
    """

    def __init__(
        self,
        filename=None,
        mode="a",
        encoding=None,
        delay=False,
        format: str = LOG_FORMAT_STR,
    ):
        """
        Initialize the handler.

        Args:
            filename (str): Path to the log file. If None, logs to stderr.
            mode (str): File mode (default: 'a' for append).
            encoding (str): File encoding (default: None).
            delay (bool): Delay file creation until the first emit (default: False).
            format (Optional, str): format string.  Defaults to {0}
        """
        ExitOnExceptionHandler.__init__.__doc__ = (
            ExitOnExceptionHandler.__init__.__doc__.format(LOG_FORMAT_STR)
        )

        if filename:
            super().__init__()
            self.handler = logging.FileHandler(filename, mode, encoding, delay)
        else:
            super().__init__()
            self.handler = logging.StreamHandler()

        self.handler.setFormatter(logging.Formatter(format))

    def emit(self, record):
        self.handler.emit(record)
        if record.levelno in (logging.ERROR, logging.CRITICAL):
            raise SystemExit(-1)


class ExitOnCriticalExceptionHandler(logging.Handler):
    """Logging exception handler that catches CRITICAL
    level logging and exits (does not exit on ERRORS).
    Logs to a file or stderr based on configuration.
    see https://stackoverflow.com/a/48201163
    """

    def __init__(
        self,
        filename=None,
        mode="a",
        encoding=None,
        delay=False,
        format: str = LOG_FORMAT_STR,
    ):
        """
        Initialize the handler.

        Args:
            filename (str): Path to the log file. If None, logs to stderr.
            mode (str): File mode (default: 'a' for append).
            encoding (str): File encoding (default: None).
            delay (bool): Delay file creation until the first emit (default: False).
            format (Optional, str): format string.  Defaults to {0}
        """
        ExitOnCriticalExceptionHandler.__init__.__doc__ = (
            ExitOnCriticalExceptionHandler.__init__.__doc__.format(LOG_FORMAT_STR)
        )
        if filename:
            super().__init__()
            self.handler = logging.FileHandler(filename, mode, encoding, delay)
        else:
            super().__init__()
            self.handler = logging.StreamHandler()

        self.handler.setFormatter(logging.Formatter(format))

    def emit(self, record):
        self.handler.emit(record)
        if record.levelno == logging.CRITICAL:
            raise SystemExit(-1)


def _timed(fn):
    """Universal timing decorator for sync and async functions, for debugging only"""

    @wraps(fn)
    def sync_wrapper(*args, **kwargs):
        logger = logging.getLogger(fn.__name__)

        # only start the counter if in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            start = perf_counter()
            logger.debug(f"Entering {fn.__name__}")

        result = fn(*args, **kwargs)

        if logger.isEnabledFor(logging.DEBUG):
            elapsed = perf_counter() - start
            logger.debug(f"Exiting {fn.__name__} ELAPSED TIME: {elapsed:0.4f} seconds")

        return result

    @wraps(fn)
    async def async_wrapper(*args, **kwargs):
        logger = logging.getLogger(fn.__name__)
        # only start the counter if in debug mode
        if logger.isEnabledFor(logging.DEBUG):
            start = perf_counter()
            logger.debug(f"Entering {fn.__name__}")

        result = await fn(*args, **kwargs)

        if logger.isEnabledFor(logging.DEBUG):
            elapsed = perf_counter() - start
            logger.debug(f"Exiting {fn.__name__} ELAPSED TIME: {elapsed:0.4f} seconds")

        return result

    if asyncio.iscoroutinefunction(fn):
        return async_wrapper
    return sync_wrapper


timed = _timed
async_timed = _timed


def setup_root_logger(
    level: int = logging.INFO,
    log_file: str | None = None,
    format_str: str = LOG_FORMAT_STR,
) -> None:
    """
    Configure the root logger with sensible defaults.

    Sets up console (stderr) or file logging based on parameters.
    Exits on ERROR or CRITICAL level logs.

    Args:
        level (int): Logging level (default: logging.INFO).
        log_file (Optional[str]): Path to log file. If None, logs to stderr.
            If provided, creates a file handler instead of console.
        format_str (str): Log format string (default: LOG_FORMAT_STR).

    Example:
        # Log to console (stderr)
        setup_root_logger(level=logging.DEBUG)

        # Log to file
        setup_root_logger(level=logging.INFO, log_file="app.log")
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    handler = ExitOnExceptionHandler(filename=log_file, format=format_str)
    handler.setLevel(level)
    root_logger.addHandler(handler)
