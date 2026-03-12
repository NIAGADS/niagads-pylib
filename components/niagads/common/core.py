import logging

from niagads.utils.logging import FunctionContextLoggerWrapper, LOG_FORMAT_STR


class ComponentBaseMixin:
    """
    Generic base class with debug, logger, and verbose members.
    """

    def __init__(self, debug: bool = False, verbose: bool = False):
        self._debug: bool = debug
        self._verbose: bool = verbose

        logger = logging.getLogger(self.__class__.__module__)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT_STR))
        logger.addHandler(handler)

        self.logger: logging.Logger = FunctionContextLoggerWrapper(logger=logger)

        if self._debug:
            self.logger.setLevel(logging.DEBUG)
