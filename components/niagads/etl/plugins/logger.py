import logging
import json
from typing import Any, Dict


class ETLJSONFormatter(logging.Formatter):
    """
    Formats log records as single-line JSON for ETL runs.

    All records are output as JSON with consistent keys where available.
    Checkpoints are easily discoverable with: {"message": "CHECKPOINT", ...}
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format a log record as a JSON string.

        Args:
            record (logging.LogRecord): The log record to format.

        Returns:
            str: The formatted JSON string.
        """
        base: Dict[str, Any] = {
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Standard ETL context
        for attr in [
            "plugin",
            "run_id",
            "status",
            "rows",
            "runtime",
            "memory",
            "line",
            "record",
            "error",
            "params",
            "task_id",
        ]:
            if hasattr(record, attr):
                base[attr] = getattr(record, attr)
        # Include all fields from extra if present and not already in base
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            for k, v in record.extra.items():
                if k not in base:
                    base[k] = v
        return json.dumps(base, ensure_ascii=False)


class ETLLogger:
    """
    ETL-specific JSON logger.

    Always logs in JSON format and includes run_id and plugin in all logs.
    Checkpoints are logged at ERROR level with message="CHECKPOINT".
    """

    def __init__(self, name: str, log_file: str, run_id: str, plugin: str):
        """
        Initialize the ETLLogger.

        Args:
            name (str): Logger name.
            log_file (str): Path to the log file.
            run_id (str): Unique run identifier.
            plugin (str): Plugin name.
        """
        self.__logger = logging.getLogger(name)
        self.__logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file, mode="w")  # Overwrite log file each run
        handler.setFormatter(ETLJSONFormatter())
        self.__logger.handlers.clear()
        self.__logger.addHandler(handler)
        self.__run_id = run_id
        self.__plugin = plugin

    def flush(self):
        """
        Flush all handlers for this logger.

        Ensures that all log records are written to disk immediately by calling
        flush() on each handler. Useful for forcing log persistence after critical events.
        """
        for h in self.__logger.handlers:
            try:
                h.flush()
            except Exception:
                pass

    def info(self, message: str, **kwargs):
        """
        Log an info-level message.

        Args:
            message (str): The log message.
            **kwargs: Additional context fields to include in the log.
        """
        self.__logger.info(
            message, extra={"run_id": self.__run_id, "plugin": self.__plugin, **kwargs}
        )

    def error(self, message: str, **kwargs):
        """
        Log an error-level message.

        Args:
            message (str): The log message.
            **kwargs: Additional context fields to include in the log.
        """
        self.__logger.error(
            message, extra={"run_id": self.__run_id, "plugin": self.__plugin, **kwargs}
        )
        self.flush()

    def exception(self, message: str, **kwargs):
        """
        Log an exception with traceback at error level.

        Args:
            message (str): The log message.
            **kwargs: Additional context fields to include in the log.
        """
        self.__logger.exception(
            message, extra={"run_id": self.__run_id, "plugin": self.__plugin, **kwargs}
        )
        self.flush()

    def status(self, status: str, rows: int, runtime: float, memory_mb: float):
        """
        Log a status update for the ETL run.

        Args:
            status (str): Status message.
            rows (int): Number of rows processed.
            runtime (float): Runtime in seconds.
            memory_mb (float): Memory usage in megabytes.
        """
        self.__logger.info(
            status,
            extra={
                "run_id": self.__run_id,
                "plugin": self.__plugin,
                "status": status,
                "rows": rows,
                "runtime": f"{runtime:.2f}s",
                "memory": f"{memory_mb:.2f}MB",
            },
        )
        self.flush()

    def checkpoint(self, line: int, record: Any, error: Exception | None = None):
        """
        Log a resume checkpoint for ETL recovery.

        Args:
            line (int): Line number of the checkpoint.
            record (Any): The record at the checkpoint.
            error (Exception | None): The error encountered, if any.

        Example:
            jq 'select(.message=="CHECKPOINT")' etl.log
        """
        self.__logger.error(
            "CHECKPOINT",
            extra={
                "run_id": self.__run_id,
                "plugin": self.__plugin,
                "line": line,
                "record": record,
                "error": str(error) if error else None,
            },
        )
        self.flush()

    def init_status(
        self, plugin_name: str, params: dict, run_id: str, task_id: Any = None
    ):
        """
        Log the initialization status for a plugin run.

        Args:
            plugin_name (str): Name of the plugin.
            params (dict): Parameter name/value pairs.
            run_id (str): Unique run identifier.
            task_id (Any): Task/log id from the database, if available.
        """
        self.__logger.info(
            "INIT",
            extra={
                "plugin": plugin_name,
                "params": params,
                "run_id": run_id,
                "task_id": task_id,
            },
        )
        self.flush()

    def warning(self, message: str, **kwargs):
        """
        Log a warning-level message.

        Args:
            message (str): The log message.
            **kwargs: Additional context fields to include in the log.
        """
        self.__logger.warning(
            message, extra={"run_id": self.__run_id, "plugin": self.__plugin, **kwargs}
        )
        self.flush()

    def debug(self, message: str, **kwargs):
        """
        Log a debug-level message.

        Args:
            message (str): The log message.
            **kwargs: Additional context fields to include in the log.
        """
        self.__logger.debug(
            message, extra={"run_id": self.__run_id, "plugin": self.__plugin, **kwargs}
        )
        self.flush()

    @property
    def level(self):
        return self.__logger.level

    @level.setter
    def level(self, value):
        # Accept either int or str
        if isinstance(value, str):
            value = value.upper()
            value = logging._nameToLevel.get(value, logging.INFO)
        self.__logger.setLevel(value)
