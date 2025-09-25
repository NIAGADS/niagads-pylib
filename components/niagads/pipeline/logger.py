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
        if hasattr(record, "plugin"):
            base["plugin"] = record.plugin
        if hasattr(record, "run_id"):
            base["run_id"] = record.run_id
        if hasattr(record, "status"):
            base["status"] = record.status
        if hasattr(record, "rows"):
            base["rows"] = record.rows
        if hasattr(record, "runtime"):
            base["runtime"] = record.runtime
        if hasattr(record, "memory"):
            base["memory"] = record.memory
        # Checkpoint fields
        if hasattr(record, "line"):
            base["line"] = record.line
        if hasattr(record, "record"):
            base["record"] = record.record
        if hasattr(record, "error"):
            base["error"] = record.error
        # Extra passthrough (optional)
        if hasattr(record, "extra"):
            base["extra"] = record.extra
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
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_file)
        handler.setFormatter(ETLJSONFormatter())
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.run_id = run_id
        self.plugin = plugin

    def info(self, message: str, **kwargs):
        """
        Log an info-level message.

        Args:
            message (str): The log message.
            **kwargs: Additional context fields to include in the log.
        """
        self.logger.info(
            message, extra={"run_id": self.run_id, "plugin": self.plugin, **kwargs}
        )

    def error(self, message: str, **kwargs):
        """
        Log an error-level message.

        Args:
            message (str): The log message.
            **kwargs: Additional context fields to include in the log.
        """
        self.logger.error(
            message, extra={"run_id": self.run_id, "plugin": self.plugin, **kwargs}
        )

    def exception(self, message: str, **kwargs):
        """
        Log an exception with traceback at error level.

        Args:
            message (str): The log message.
            **kwargs: Additional context fields to include in the log.
        """
        self.logger.exception(
            message, extra={"run_id": self.run_id, "plugin": self.plugin, **kwargs}
        )

    def status(self, status: str, rows: int, runtime: float, memory_mb: float):
        """
        Log a status update for the ETL run.

        Args:
            status (str): Status message.
            rows (int): Number of rows processed.
            runtime (float): Runtime in seconds.
            memory_mb (float): Memory usage in megabytes.
        """
        self.logger.info(
            status,
            extra={
                "run_id": self.run_id,
                "plugin": self.plugin,
                "status": status,
                "rows": rows,
                "runtime": f"{runtime:.2f}s",
                "memory": f"{memory_mb:.2f}MB",
            },
        )

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
        self.logger.error(
            "CHECKPOINT",
            extra={
                "run_id": self.run_id,
                "plugin": self.plugin,
                "line": line,
                "record": record,
                "error": str(error) if error else None,
            },
        )
