import logging

from niagads.utils.logging import FunctionContextAdapter


class ComponentBaseMixin:
    """
    Generic base class with debug, logger, and verbose members.
    """
    logger: logging.Logger = FunctionContextAdapter(
        logging.getLogger(__name__), {}
    )


    def __init__(self, debug: bool = False, verbose: bool = False):
        self._debug: bool = debug
        self._verbose: bool = verbose
