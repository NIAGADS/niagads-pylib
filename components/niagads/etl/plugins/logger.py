import logging
from typing import Any, Dict, Optional
from niagads.enums.common import ProcessStatus
from niagads.etl.config import ETLMode
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.utils.logging import LOG_FORMAT_STR, FunctionContextAdapter, timed
from pydantic import BaseModel, Field, field_validator


class ETLContextAdapter(FunctionContextAdapter):
    """
    Logger adapter that injects run_id, plugin, and task_id into every log record.
    """

    def __init__(self, logger, run_id, plugin, task_id=None):
        super().__init__(logger, {})
        self.run_id = run_id
        self.plugin = plugin
        self.task_id = task_id

    def process(self, msg, kwargs):
        # Add context fields to the record
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"]["run_id"] = self.run_id
        kwargs["extra"]["plugin"] = self.plugin
        if self.task_id is not None:
            kwargs["extra"]["task_id"] = self.task_id
        return super().process(msg, kwargs)


class ETLStatusReport(BaseModel):
    """
    Status report for ETL operations.
    All fields are optional and default to None, but updates/inserts are set to {} if None.
    - updates: dict of {schema.table: count}
    - inserts: dict of {schema.table: count}
    - skips: number of skipped records
    - status: ProcessStatus (SUCCESS or FAIL)
    - mode: ETLMode
    - test: True if test mode
    - runtime: float, elapsed time in seconds
    - memory: float, memory usage in MB
    """

    updates: Optional[Dict[str, int]] = None
    inserts: Optional[Dict[str, int]] = None
    skips: Optional[int] = 0
    status: ProcessStatus
    mode: ETLMode
    test: Optional[bool] = None
    runtime: Optional[float] = None
    memory: Optional[float] = None

    @field_validator("updates", "inserts", mode="after")
    def set_dict_if_none(cls, v):
        return v if v is not None else {}


class ETLLogger:
    """
    ETL-specific text logger using ETLContextAdapter.
    Always logs in human-readable text format and includes run_id, plugin, and task_id in all logs automatically.
    """

    def __init__(self, name: str, log_file: str, run_id: str, plugin: str, task_id: Any = None, debug: bool = False):
        self.__logger = ETLContextAdapter(logging.getLogger(name), run_id, plugin, task_id)
        self.__logger.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file, mode="w")
        handler.setFormatter(logging.Formatter(LOG_FORMAT_STR))
        self.__logger.logger.handlers.clear()
        self.__logger.logger.addHandler(handler)
        self._debug = debug

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        self._debug = bool(value)

    def flush(self):
        for h in self.__logger.logger.handlers:
            try:
                h.flush()
            except Exception:
                pass

    def info(self, message: str):
        self.__logger.info(message)

    def error(self, message: str):
        self.__logger.error(message)

    def exception(self, message: str):
        if self._debug:
            self.__logger.exception(message)
        else:
            self.__logger.error(message)

    def checkpoint(self, line: Optional[int] = None, record: Optional[Any] = None, error: Optional[Exception]= None):
        checkpoint = []
        if line is not None:
            checkpoint.append(f"line={line}")
        if record is not None:
            checkpoint.append(f"record={record}")
        self.info("RESUME CHECKPONT: " + ";".join(checkpoint))
        if error is not None:
            self.error(f"RESUME CHECKPOINT ERROR: {error}")
        self.flush()

    def warning(self, message: str):
        self.__logger.warning(message)

    def debug(self, message: str):
        self.__logger.debug(message)

    def report_section(self, section: str):
        """
        Log a section header for reporting.
        """
        self.info(f"==== {section} ====")

    def report(self, section: str, **fields):
        """
        Generic reporting method: logs a section header and key/value pairs.
        Usage: logger.report('Status', parsed=100, skipped=5, loaded=95)
        """
        self.report_section(section)
        for key, value in fields.items():
            self.info(f"{key}: {value}")

    def report_config(self, params: BasePluginParams):
        """
        Log the configuration for the plugin run from a Pydantic parameter object.
        Usage: logger.report_config(params)
        """
        # Log plugin name from logger name
        self.info(f"Running ETL Plugin: {self.__logger.logger.name}")
        self.report_section("ETL Plugin Config")
        config = params.model_dump()
        for key, value in config.items():
            self.info(f"{key.upper()}: {value}")

    def status(self, status: ETLStatusReport):
        """
        Log ETL status from an ETLStatusReport model.
        Logs zero if inserts/updates are empty.
        """
        section = "DONE WITH TEST" if status.test else "DONE"
        self.report_section(section)
        self.info(f"Transaction Mode: {status.mode}")
        if status.runtime is not None:
            self.info(f"RUNTIME: {status.runtime:.2f}s")
        if status.memory is not None:
            self.info(f"MEMORY: {status.memory:.2f}MB")
            
        # Log inserts
        if status.inserts:
            for table, count in status.inserts.items():
                self.info(f"INSERTED {count} records into {table}")
        else:
            self.info("INSERTED 0 records.")
            
        # Log updates
        if status.updates:
            for table, count in status.updates.items():
                self.info(f"UPDATED {count} records in {table}")
        else:
            self.info("UPDATED 0 records.")
            
        self.info(f"SKIPPED {status.skips} records.")

        self.info(str(status.status))

    @property
    def level(self):
        return self.__logger.logger.level

    @level.setter
    def level(self, value):
        if isinstance(value, str):
            value = value.upper()
            value = logging._nameToLevel.get(value, logging.INFO)
        self.__logger.logger.setLevel(value)
