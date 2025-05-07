import logging
from functools import wraps
from time import perf_counter

LOG_FORMAT_STR: str = "%(asctime)s %(funcName)s %(levelname)-8s %(message)s"


class ExitOnExceptionHandler(logging.Handler):
    """Logging exception handler that catches ERRORS and CRITICAL
    level logging and exits.
    Logs to a file or stderr based on configuration.
    see https://stackoverflow.com/a/48201163
    """

    def __init__(self, filename=None, mode="a", encoding=None, delay=False):
        """
        Initialize the handler.

        Args:
            filename (str): Path to the log file. If None, logs to stderr.
            mode (str): File mode (default: 'a' for append).
            encoding (str): File encoding (default: None).
            delay (bool): Delay file creation until the first emit (default: False).
        """
        if filename:
            super().__init__()
            self.handler = logging.FileHandler(filename, mode, encoding, delay)
        else:
            super().__init__()
            self.handler = logging.StreamHandler()

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

    def __init__(self, filename=None, mode="a", encoding=None, delay=False):
        """
        Initialize the handler.

        Args:
            filename (str): Path to the log file. If None, logs to stderr.
            mode (str): File mode (default: 'a' for append).
            encoding (str): File encoding (default: None).
            delay (bool): Delay file creation until the first emit (default: False).
        """
        if filename:
            super().__init__()
            self.handler = logging.FileHandler(filename, mode, encoding, delay)
        else:
            super().__init__()
            self.handler = logging.StreamHandler()

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
