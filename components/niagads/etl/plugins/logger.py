import logging
from typing import Any, Optional


from niagads.common.types import ETLOperation
from niagads.etl.plugins.types import ETLRunStatus, ResumeCheckpoint
from niagads.etl.types import ETLExecutionMode
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.loaders.core import Settings
from niagads.utils.logging import (
    LOG_FORMAT_STR,
    ExitOnExceptionHandler,
    FunctionContextLoggerWrapper,
)

import sqlalchemy.log


class ETLLogger:
    """
    ETL-specific text logger
    Always logs in human-readable text format and includes run_id, plugin, and task_id in all logs automatically.
    """

    def __init__(self, name: str, log_file: str, debug: bool = False):
        self._debug = debug
        logger = logging.getLogger(name)  # , run_id=run_id)# , plugin, task_id)
        handler = ExitOnExceptionHandler(
            filename=log_file, mode="w", format=LOG_FORMAT_STR
        )
        logger.addHandler(handler)

        # deal with sqlalchemy echo in debug+verbose mode
        sqlalchemy.log._add_default_handler = lambda x: None
        sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
        sqlalchemy_logger.handlers.clear()  # Remove all existing handlers
        sqlalchemy_logger.addHandler(handler)
        sqlalchemy_logger.propagate = False  # Prevent propagation to root logger

        if self._debug:
            self.__logger: logging.Logger = FunctionContextLoggerWrapper(logger=logger)
            self.__logger.setLevel(logging.DEBUG)
            sqlalchemy_logger.setLevel(logging.DEBUG)

        else:
            self.__logger = logger
            self.__logger.setLevel(logging.INFO)
            sqlalchemy_logger.setLevel(logging.INFO)

    def flush(self):
        for h in self.__logger.handlers:
            try:
                h.flush()
            except Exception:
                pass

    def _format_message(self, *args):
        """
        Simple string formatting for all arguments. No pretty-printing of complex objects.
        """
        return " ".join(str(arg) for arg in args)

    def info(self, *args):
        self.__logger.info(self._format_message(*args))

    def error(self, *args):
        self.__logger.error(self._format_message(*args))

    def critical(self, *args):
        self.__logger.critical(self._format_message(*args))

    def exception(self, *args):
        if self._debug:
            self.__logger.exception(self._format_message(*args))
        else:
            self.__logger.error(self._format_message(*args))

    def warning(self, *args):
        self.__logger.warning(self._format_message(*args))

    def debug(self, *args):
        self.__logger.debug(self._format_message(*args))

    def report_section(
        self, section: str, width: int = 60, char: str = "-", returnStr: bool = False
    ):
        """
        Log a visually distinct, centered section header for reporting.
        """
        title = f" {section} "
        pad = width - len(title)
        left = char * (pad // 2)
        right = char * (pad - len(left))
        header = f"{left}{title}{right}"
        if returnStr:
            return header
        self.info("")
        self.info(f"{header}")

    def report_section_end(self, section: str, width: int = 60, char: str = "-"):
        sectionText = self.report_section(section, width, char, returnStr=True)
        self.info(f"{char * len(sectionText)}")
        self.info("")

    def report(self, section: str, **fields):
        """
        Generic reporting method: logs a section header and key/value pairs.
        Usage: logger.report('Status', parsed=100, skipped=5, loaded=95)
        """
        self.report_section(section)
        for key, value in fields.items():
            self.info(f"{key}: {value}")

    def log_plugin_configuration(self, params: BasePluginParams):
        """
        Log the configuration for the plugin run from a Pydantic parameter object.
        Usage: logger.report_config(params)
        """
        # Log plugin name from logger name
        self.info(f"Running ETL Plugin: {self.__logger.name}")
        self.info("")
        self.report_section("ETL Plugin Config")
        config = params.model_dump()
        max_key_len = max(len(str(k)) for k in config.keys()) if config else 12
        for key, value in config.items():
            if key == "connection_string" and value is None:
                value = Settings.from_env().DATABASE_URI
            self.info(f"{key.upper():<{max_key_len}} : {value}")
        self.report_section_end("ETL Plugin Config")

    def log_plugin_run_start(self):
        self.report_section("ETL Plugin Run")

    def log_plugin_run_id(self, run_id):
        keyw = 16
        self.info(f"{'RUN ID':<{keyw}} : {run_id}")

    def checkpoint(self, checkpoint: ResumeCheckpoint):
        self.report_section("ETL Resume Checkpoint")
        self.info(f"CHECKPOINT: {checkpoint.as_info_string(self._debug)}")
        self.report_section_end("ETL Resume Checkpoint")
        self.flush()

    def status(self, status: ETLRunStatus):
        """
        Log ETL status from an ETLStatusReport model.
        Logs zero if inserts/updates are empty.
        """

        prefix = "TEST" if status.mode == ETLExecutionMode.DRY_RUN else "RUN"
        self.report_section(f"{prefix} Transaction Summary")
        keyw = 16

        self.info(f"{'STATUS':<{keyw}} : {str(status.status)}")
        self.info(f"{'MODE':<{keyw}} : {status.mode}")
        self.info(f"{'COMMIT':<{keyw}} : {status.commit}")
        self.info(f"{'RUN ID':<{keyw}} : {status.run_id}")

        tx_count = status.total_transactions()
        if status.mode == ETLExecutionMode.DRY_RUN:
            self.info(f"{'PROCESSED':<{keyw}} : {tx_count}  records.")
        else:
            # log writes

            self.info(f"{'TOTAL TRANSACTIONS':<{keyw}} : {tx_count}")

            transactions = status.transaction_record or {}
            if len(transactions) > 0:
                for table, table_transactions in status.transaction_record.items():
                    for operation, count in table_transactions.items():
                        op = f"{ETLOperation(operation).past_tense()}"
                        self.info(f"{str(op):<{keyw}} : {count} records in {table}")
            else:
                self.info(f"{str(status.operation):<{keyw}} : 0 records")

        if status.runtime is not None:
            self.info(f"{'RUNTIME':<{keyw}} : {status.runtime:.2f}s")

        if status.memory is not None:
            self.info(f"{'MEMORY':<{keyw}} : {status.memory:.2f}MB")

        self.report_section_end("Transaction Summary")

    @property
    def level(self):
        return self.__logger.level

    @level.setter
    def level(self, value):
        if isinstance(value, str):
            value = value.upper()
            value = logging._nameToLevel.get(value, logging.INFO)
        self.__logger.setLevel(value)
