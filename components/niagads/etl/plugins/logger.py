import logging
from typing import Any, Optional


from niagads.etl.plugins.types import ETLRunStatus
from niagads.etl.types import ETLMode
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.loaders.core import Settings
from niagads.utils.logging import (
    LOG_FORMAT_STR,
    ExitOnExceptionHandler,
    FunctionContextLoggerWrapper,
)


class ETLLogger:
    """
    ETL-specific text logger
    Always logs in human-readable text format and includes run_id, plugin, and task_id in all logs automatically.
    """

    def __init__(
        self,
        name: str,
        log_file: str,
        debug: bool = False,
    ):
        logger = logging.getLogger(name)  # , run_id=run_id)# , plugin, task_id)
        handler = logging.FileHandler(log_file, mode="w")
        handler.setFormatter(logging.Formatter(LOG_FORMAT_STR))

        logger.addHandler(handler)

        self._debug = debug

        if self._debug:
            self.__logger: logging.Logger = FunctionContextLoggerWrapper(logger=logger)
            self.__logger.setLevel(logging.DEBUG)

        else:
            self.__logger = logger
            self.__logger.setLevel(logging.INFO)

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

    def log_plugin_run(self):
        self.report_section("ETL Plugin Run")

    def checkpoint(
        self,
        line: Optional[int] = None,
        record: Optional[Any] = None,
        record_id: Optional[str] = None,
        error: Optional[Exception] = None,
    ):
        self.report_section("ETL Resume Checkpoint")
        checkpoint = []
        if line is not None:
            checkpoint.append(f"line={line}")
        if record_id is not None:
            checkpoint.append(f"record_id={record_id}")
        if record is not None:
            checkpoint.append(f"record={record}")
        self.info("CHECKPOINT:", ";".join(checkpoint))
        if error is not None:
            self.error(f"ERROR: {error}")
        self.report_section_end("ETL Resume Checkpoint")
        self.flush()

    def status(self, status: ETLRunStatus):
        """
        Log ETL status from an ETLStatusReport model.
        Logs zero if inserts/updates are empty.
        """

        prefix = "TEST" if status.mode == ETLMode.DRY_RUN else "RUN"
        self.report_section(f"{prefix} Transaction Summary")
        keyw = 16
        self.info(f"{'MODE':<{keyw}} : {status.mode}")
        self.info(f"{'TASK ID':<{keyw}} : {status.task_id}")

        if status.runtime is not None:
            self.info(f"{'RUNTIME':<{keyw}} : {status.runtime:.2f}s")

        if status.memory is not None:
            self.info(f"{'MEMORY':<{keyw}} : {status.memory:.2f}MB")

        tx_count = status.total_transactions()
        if status.mode == ETLMode.DRY_RUN:
            self.info(f"{'PROCESSED':<{keyw}} : {tx_count}  records.")

        else:
            # log writes

            self.info(f"{'WROTE':<{keyw}} : {tx_count} records.")

            transactions = status.transaction_record or {}
            if len(transactions) > 0:
                for table, record_count in status.transaction_record.items():
                    self.info(
                        f"{str(status.operation):<{keyw}} : {record_count} records into {table}"
                    )
            else:
                self.info(f"{str(status.operation):<{keyw}} : 0 records")

        self.info(f"{'STATUS':<{keyw}} : {str(status.status)}")
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
