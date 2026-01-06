import logging
from typing import Any, Dict, Optional, Union

from niagads.enums.common import ProcessStatus
from niagads.etl.config import ETLMode
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.genomicsdb.models.admin.pipeline import ETLOperation
from niagads.utils.logging import LOG_FORMAT_STR
from pydantic import BaseModel


class ETLStatusReport(BaseModel):
    """
    Status report for ETL operations.
    """

    transactions: Dict[ETLOperation, Dict[str, int]] = {}
    status: ProcessStatus
    mode: ETLMode
    test: bool = False
    runtime: Optional[float] = None
    memory: Optional[float] = None
    task_id: Union[ETLMode, int]

    def _validate_key_format(self, key: str):
        """
        Ensure key is in 'schema.table' format.
        """
        if not isinstance(key, str) or "." not in key or key.count(".") != 1:
            raise ValueError(
                "Table must be qualified by a schema (e.g., 'myschema.mytable')."
            )

    def increment_transaction(self, operation, table: str, count: int = 1):
        """
        Increment the count for a given ETLOperation and table.
        """
        self._validate_key_format(table)

        if ETLOperation(operation) not in self.transactions:
            self.transactions[operation] = {}
        self.transactions[operation][table] = (
            self.transactions[operation].get(table, 0) + count
        )

    def total_writes(self) -> int:
        """
        Return the total number of records written.
        """
        total = 0
        for operation, table_counts in self.transactions.items():
            if operation not in [ETLOperation.SKIP, ETLOperation.DELETE]:
                total += sum(table_counts.values())
        return total

    def total_skips(self) -> int:
        """
        Return the total number of skipped records
        """
        if ETLOperation.SKIP in self.transactions:
            return sum(self.transactions[ETLOperation.SKIP].values())
        return 0

    def total_deletes(self) -> int:
        """
        Return the total number of deleted records.
        """
        if ETLOperation.DELETE in self.transactions:
            return sum(self.transactions[ETLOperation.DELETE].values())
        return 0


class ETLLogger:
    """
    ETL-specific text logger
    Always logs in human-readable text format and includes run_id, plugin, and task_id in all logs automatically.
    """

    def __init__(
        self,
        name: str,
        log_file: str,
        run_id: str,
        plugin: str,
        task_id: Any = None,
        debug: bool = False,
    ):
        self.__logger = logging.getLogger(name)  # , run_id=run_id)# , plugin, task_id)
        self.__logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file, mode="w")
        handler.setFormatter(logging.Formatter(LOG_FORMAT_STR))
        self.__logger.handlers.clear()
        self.__logger.addHandler(handler)
        self._debug = debug

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
            self.info(f"{key.upper():<{max_key_len}} : {value}")
        self.report_section_end("ETL Plugin Config")

    def log_plugin_run(self):
        self.report_section("ETL Plugin Run")

    def checkpoint(
        self,
        line: Optional[int] = None,
        record: Optional[Any] = None,
        error: Optional[Exception] = None,
    ):
        self.report_section("ETL Resume Checkpoint")
        checkpoint = []
        if line is not None:
            checkpoint.append(f"line={line}")
        if record is not None:
            checkpoint.append(f"record={record}")
        self.info("CHECKPOINT:", ";".join(checkpoint))
        if error is not None:
            self.error(f"ERROR: {error}")
        self.report_section_end("ETL Resume Checkpoint")
        self.flush()

    def status(self, status: ETLStatusReport):
        """
        Log ETL status from an ETLStatusReport model.
        Logs zero if inserts/updates are empty.
        """

        prefix = "TEST" if status.test else "RUN"
        self.report_section(f"{prefix} Transaction Summary")
        keyw = 16
        self.info(f"{'MODE':<{keyw}} : {status.mode}")
        self.info(f"{'TASK ID':<{keyw}} : {status.task_id}")

        if status.runtime is not None:
            self.info(f"{'RUNTIME':<{keyw}} : {status.runtime:.2f}s")

        if status.memory is not None:
            self.info(f"{'MEMORY':<{keyw}} : {status.memory:.2f}MB")

        # log writes
        count = status.total_writes()
        if status.mode == ETLMode.DRY_RUN:
            self.info(f"{'PROCESSED':<{keyw}} : {count} records.")

        else:
            self.info(f"{'WROTE':<{keyw}} : {count} records.")

            # log transaction types, iterating over reference
            # to ensure order is consistent when logging

            for operation in ETLOperation.list():
                for table, record_count in status.transactions[str(operation)].items():
                    self.info(
                        f"{str(operation):<{keyw}} : {record_count} records into {table}"
                    )
            else:
                self.info(f"{str(operation):<{keyw}} : 0 records")

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
