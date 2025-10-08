import logging
from typing import Any, Dict, Optional
from niagads.enums.common import ProcessStatus
from niagads.etl.config import ETLMode
from niagads.etl.plugins.parameters import BasePluginParams
from niagads.utils.logging import LOG_FORMAT_STR
from pydantic import BaseModel, field_validator



class ETLStatusReport(BaseModel):
    """
    Status report for ETL operations.
    """

    updates: Optional[Dict[str, int]] = {}
    inserts: Optional[Dict[str, int]] = {}
    skips: Optional[int] = 0
    status: ProcessStatus
    mode: ETLMode
    test: Optional[bool] = None
    runtime: Optional[float] = None
    memory: Optional[float] = None
    task_id: int 

    def _validate_key_format(self, key: str):
        """
        Ensure key is in 'schema.table' format.
        """
        if not isinstance(key, str) or '.' not in key or key.count('.') != 1:
            raise ValueError("Table must be qualified by a schema (e.g., 'myschema.mytable').")

    def _increment_dict(self, d: Optional[Dict[str, int]], key: str, count: int = 1) -> Dict[str, int]:
        self._validate_key_format(key)
        if d is None:
            d = {}
        d[key] = d.get(key, 0) + count
        return d

    def increment_inserts(self, key: str, count: int = 1):
        """
        Increment the count for a key in 'inserts'. Adds the key if it does not exist.
        """
        self.inserts = self._increment_dict(self.inserts, key, count)

    def increment_updates(self, key: str, count: int = 1):
        """
        Increment the count for a key in 'updates'. Adds the key if it does not exist.
        """
        self.updates = self._increment_dict(self.updates, key, count)



class ETLLogger:
    """
    ETL-specific text logger using ETLContextAdapter.
    Always logs in human-readable text format and includes run_id, plugin, and task_id in all logs automatically.
    """

    def __init__(self, name: str, log_file: str, run_id: str, plugin: str, task_id: Any = None, debug: bool = False):
        self.__logger = logging.getLogger(name)# , run_id=run_id)# , plugin, task_id)
        self.__logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file, mode="w")
        handler.setFormatter(logging.Formatter(LOG_FORMAT_STR))
        self.__logger.handlers.clear()
        self.__logger.addHandler(handler)
        self._debug = debug

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        self._debug = bool(value)

    def flush(self):
        for h in self.__logger.handlers:
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
        self.info("RESUME CHECKCOVERT: " + ";".join(checkpoint))
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

    def log_plugin_configuration(self, params: BasePluginParams):
        """
        Log the configuration for the plugin run from a Pydantic parameter object.
        Usage: logger.report_config(params)
        """
        # Log plugin name from logger name
        self.info(f"Running ETL Plugin: {self.__logger.name}")
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
        self.info(f"TASK ID: {status.task_id}")
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
        return self.__logger.level

    @level.setter
    def level(self, value):
        if isinstance(value, str):
            value = value.upper()
            value = logging._nameToLevel.get(value, logging.INFO)
        self.__logger.setLevel(value)
