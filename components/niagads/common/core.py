import logging

from niagads.utils.logging import (
    ExitOnExceptionHandler,
    FunctionContextLoggerWrapper,
    LOG_FORMAT_STR,
)


class ComponentBaseMixin:
    """
    Generic base class with debug, logger, and verbose members.
    """

    def __init__(self, debug: bool = False, verbose: bool = False):
        self._debug: bool = debug
        self._verbose: bool = verbose

        logger = logging.getLogger(self.__class__.__module__)
        handler = ExitOnExceptionHandler(format=LOG_FORMAT_STR)
        logger.addHandler(handler)

        if self._debug:
            self.logger: logging.Logger = FunctionContextLoggerWrapper(logger=logger)
        else:
            self.logger = logger

        if self._debug:
            self.logger.setLevel(logging.DEBUG)
