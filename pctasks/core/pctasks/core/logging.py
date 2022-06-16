"""Logging to Azure Application Insights
"""
import logging
import os
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from opencensus.ext.azure.log_exporter import AzureEventHandler, AzureLogHandler

from pctasks.core.constants import ENV_VAR_TASK_APPINSIGHTS_KEY
from pctasks.core.models.base import RunRecordId
from pctasks.core.models.task import TaskRunConfig
from pctasks.core.storage import Storage, get_storage

logger = logging.getLogger(__name__)

DEFAULT_TASK_LOG_FORMAT = "[%(levelname)s] %(asctime)s - %(message)s"


class LogLevel(int, Enum):
    FATAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10


@lru_cache(maxsize=100)
def _get_az_loggers(
    id: str, task_logger_app_insights_key: Optional[str]
) -> Tuple[logging.Logger, logging.Logger]:
    """Returns (Traces logger, Event logger)"""
    traces_logger = logging.getLogger(f"pctasks-traceslogger-{id}")
    event_logger = logging.getLogger(f"pctasks-eventlogger-{id}")

    instrumentation_key: Optional[str] = (
        task_logger_app_insights_key
        or os.environ.get(ENV_VAR_TASK_APPINSIGHTS_KEY)
        or os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")
    )

    if instrumentation_key:
        # Set up traces logging.
        traces_logger.setLevel(logging.INFO)
        traces_handler = AzureLogHandler(
            connection_string=f"InstrumentationKey={instrumentation_key}"
        )
        traces_logger.addHandler(traces_handler)

        # Set up event logging
        event_logger.setLevel(logging.INFO)
        event_handler = AzureEventHandler(
            connection_string=f"InstrumentationKey={instrumentation_key}"
        )
        event_logger.addHandler(event_handler)
    else:
        logger.warning(
            f"Skipping Azure logging, no {ENV_VAR_TASK_APPINSIGHTS_KEY} "
            "found in environment."
        )

    return (traces_logger, event_logger)


class StorageHandler(logging.StreamHandler):
    def __init__(self, storage: Storage, log_file_path: str) -> None:
        super().__init__()
        self.storage = storage
        self.log_file_path = log_file_path
        self.lines: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        self.lines.append(msg)

    def close(self) -> None:
        if self.storage:
            self.storage.write_text(self.log_file_path, "\n".join(self.lines))


class RunLogger:
    def __init__(
        self,
        run_record_id: RunRecordId,
        logger_id: Optional[str] = None,
        app_insights_key: Optional[str] = None,
    ) -> None:
        self.run_record_id = run_record_id
        self.traces_logger, self.event_logger = _get_az_loggers(
            str(run_record_id), app_insights_key
        )
        self.logger_id = logger_id

    def _get_custom_dimensions(
        self,
        dataset_id: Optional[str] = None,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> Dict[str, str]:
        result = {"run_id": self.run_record_id.run_id}
        dataset_id = dataset_id or self.run_record_id.dataset_id
        if dataset_id:
            result["dataset_id"] = dataset_id
        job_id = job_id or self.run_record_id.job_id
        if job_id:
            result["job_id"] = job_id
        task_id = task_id or self.run_record_id.task_id
        if task_id:
            result["task_id"] = task_id
        return result

    def log_event(
        self,
        status: str,
        message: Optional[str] = None,
        properties: Optional[Dict[str, str]] = None,
    ) -> None:
        properties = properties or {}
        message = message or f"Status: {status}"
        event_message = f"new status: {status}"
        if message:
            event_message += f" - {message}"
        if self.logger_id:
            event_message = f"[{self.logger_id}]: {event_message}"
        self.event_logger.info(
            event_message,
            extra={
                "custom_dimensions": {
                    **properties,
                    **self._get_custom_dimensions(),
                }
            },
        )
        self.log(
            event_message,
            {**properties, **{"status": str(status)}},
        )

    def log(
        self,
        message: str,
        properties: Optional[Dict[str, str]] = None,
        dataset_id: Optional[str] = None,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
        level: LogLevel = LogLevel.INFO,
    ) -> None:
        if self.logger_id:
            message = f"[{self.logger_id}]: {message}"
        self.traces_logger.log(
            msg=message,
            extra={
                "custom_dimensions": {
                    **(properties or {}),
                    **self._get_custom_dimensions(
                        dataset_id=dataset_id, job_id=job_id, task_id=task_id
                    ),
                }
            },
            level=level.value,
        )

    def info(
        self,
        message: str,
        properties: Optional[Dict[str, str]] = None,
        dataset_id: Optional[str] = None,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        self.log(
            message,
            properties=properties,
            dataset_id=dataset_id,
            job_id=job_id,
            task_id=task_id,
            level=LogLevel.INFO,
        )

    def warning(
        self,
        message: str,
        properties: Optional[Dict[str, str]] = None,
        dataset_id: Optional[str] = None,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        self.log(
            message,
            properties=properties,
            dataset_id=dataset_id,
            job_id=job_id,
            task_id=task_id,
            level=LogLevel.WARNING,
        )

    def error(
        self,
        message: str,
        properties: Optional[Dict[str, str]] = None,
        dataset_id: Optional[str] = None,
        job_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> None:
        self.log(
            message,
            properties=properties,
            dataset_id=dataset_id,
            job_id=job_id,
            task_id=task_id,
            level=LogLevel.ERROR,
        )


class TaskLogger:
    """Adds a log handler which will store Task logs in local or blob storage."""

    def __init__(
        self,
        storage: Storage,
        log_file_path: str,
        package: Optional[str] = None,
        level: int = logging.INFO,
        log_format: str = DEFAULT_TASK_LOG_FORMAT,
    ) -> None:
        if package:
            logger = logging.getLogger(package)
        else:
            logger = logging.getLogger()

        handler = StorageHandler(storage, log_file_path)
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter(log_format))

        self.logger = logger
        self.handler = handler

    def __enter__(self) -> "TaskLogger":
        self.logger.addHandler(self.handler)
        return self

    def __exit__(self, *args: Any) -> None:
        if self.handler:
            self.handler.flush()
            self.logger.removeHandler(self.handler)
            self.handler.close()

    @staticmethod
    def timestamp_path(logging_dir: str, path: str) -> str:
        """Generates a unique resource name by appending a time
        string after the specified prefix.
        :param str resource_prefix: The resource prefix to use.
        :return: A string with the format "resource_prefix-<time>".
        :type: str
        """
        dir_name = os.path.dirname(path)
        base_name = os.path.basename(path)
        new_name = datetime.utcnow().strftime("%Y%m%d-%H%M%S") + f"-{base_name}"
        return os.path.join(dir_name, new_name)

    @classmethod
    def from_task_run_config(
        cls,
        task_run_config: TaskRunConfig,
        package: Optional[str] = None,
        level: int = logging.INFO,
        log_format: str = DEFAULT_TASK_LOG_FORMAT,
    ) -> "TaskLogger":
        log_storage = get_storage(
            os.path.dirname(task_run_config.log_blob_config.uri),
            sas_token=task_run_config.log_blob_config.sas_token,
            account_url=task_run_config.log_blob_config.account_url,
        )

        return cls(
            log_storage,
            log_storage.get_path(task_run_config.log_blob_config.uri),
            package,
            level,
            log_format,
        )
