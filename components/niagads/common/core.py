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

    def __init__(
        self,
        debug: bool = False,
        verbose: bool = False,
        initialize_logger: bool = True,
        logger: logging.Logger = None,
    ):
        """
        Initialize the ComponentBaseMixin with debug, verbose, and logger configuration.

        Args:
            debug (bool): Enable debug mode. Defaults to False.
            verbose (bool): Enable verbose output. Defaults to False.
            initialize_logger (bool): Whether to initialize a logger. Set to False to
                use a custom logger in derived. Defaults to True.
            logger (logging.Logger, optional): Custom logger instance. If provided,
                this logger is used instead of creating a new one. Usually used when you
                want to use the logger of a the script or class calling this one.
                Defaults to None.
        """
        self._debug: bool = debug
        self._verbose: bool = verbose

        if logger is not None:
            self.logger = logger
        else:
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
