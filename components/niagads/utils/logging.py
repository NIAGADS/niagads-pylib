import inspect
import logging
from functools import wraps
from time import perf_counter

LOG_FORMAT_STR: str = "%(asctime)s %(levelname)-8s %(message)s"


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
            className = f"{frame.f_locals["self"].__class__.__name__}:"
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


def timed(fn):
    """decorator for timing a function call"""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(fn.__name__)
        start = perf_counter()
        logger.debug("Entering %s" % fn.__name__)

        result = fn(*args, **kwargs)

        elapsed = start - perf_counter()
        logger.debug(
            "Exiting %s" % fn.__name__
            + "ELAPSED TIME: "
            + f"Elapsed time: {elapsed:0.4f} seconds"
        )

        # Return the return value
        return result

    return wrapper
