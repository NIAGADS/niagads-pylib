import logging

from niagads.utils.logging import FunctionContextLoggerWrapper


class ComponentBaseMixin:
    """
    Generic base class with debug, logger, and verbose members.
    """

    def __init__(self, debug: bool = False, verbose: bool = False):
        self._debug: bool = debug
        self._verbose: bool = verbose
        self.logger: logging.Logger = FunctionContextLoggerWrapper(
            logger=logging.getLogger(self.__class__.__module__)
        )

        if self._debug:
            self.logger.setLevel(logging.DEBUG)
