import logging
from functools import wraps
from time import perf_counter

LOG_FORMAT_STR: str = "%(asctime)s %(funcName)s %(levelname)-8s %(message)s"


class ExitOnExceptionStreamHandler(logging.StreamHandler):
    """
    logging exception handler that catches ERRORS and CRITICAL
    level logging and exits
    see https://stackoverflow.com/a/48201163
    """

    def emit(self, record):
        super().emit(record)
        if record.levelno in (logging.ERROR, logging.CRITICAL):
            raise SystemExit(-1)


class ExitOnExceptionHandler(logging.FileHandler):
    """
    logging exception handler that catches ERRORS and CRITICAL
    level logging and exits
    see https://stackoverflow.com/a/48201163
    """

    def emit(self, record):
        super().emit(record)
        if record.levelno in (logging.ERROR, logging.CRITICAL):
            raise SystemExit(-1)


class ExitOnCriticalExceptionHandler(logging.FileHandler):
    """
    logging exception handler that catches CRITICAL
    level logging and exits (does not exit on ERRORS)
    see https://stackoverflow.com/a/48201163
    """

    def emit(self, record):
        super().emit(record)
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
