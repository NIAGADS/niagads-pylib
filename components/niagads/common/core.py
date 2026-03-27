import logging

from niagads.utils.logging import (
    ExitOnExceptionHandler,
    FunctionContextLoggerWrapper,
    LOG_FORMAT_STR,
)


class ComponentBaseMixin:
    """
    Generic base class with debug, logger, and verbose members.
     - set initialize_logger = False during super().__init__ call if need to
       bypass this logging config for custom logger; e.g., ETLLogger
    """

    def __init__(
        self, debug: bool = False, verbose: bool = False, initialize_logger: bool = True
    ):
        self._debug: bool = debug
        self._verbose: bool = verbose

        if initialize_logger:
            logger = logging.getLogger(self.__class__.__module__)
            handler = ExitOnExceptionHandler(format=LOG_FORMAT_STR)
            logger.addHandler(handler)

            if self._debug:
                self.logger: logging.Logger = FunctionContextLoggerWrapper(
                    logger=logger
                )
                self.logger.setLevel(logging.DEBUG)

            else:
                self.logger = logger
