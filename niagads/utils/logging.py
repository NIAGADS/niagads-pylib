import logging

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