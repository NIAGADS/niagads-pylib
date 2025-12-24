import logging

from niagads.utils.logging import FunctionContextLoggerWrapper


class ComponentBaseMixin:
    """
    Generic base class with debug, logger, and verbose members.
    """

    logger: logging.Logger = FunctionContextLoggerWrapper(
        logger=logging.getLogger(__name__)
    )

    def __init__(self, debug: bool = False, verbose: bool = False):
        self._debug: bool = debug
        self._verbose: bool = verbose

        if self._debug:
            self.logger.setLevel = "DEBUG"
