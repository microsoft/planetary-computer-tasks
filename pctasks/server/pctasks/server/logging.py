import logging
import sys
from typing import Any, Dict, Optional, Tuple, Union, cast

from fastapi import Request
from opencensus.ext.azure.log_exporter import AzureLogHandler

import pctasks.server
from pctasks.server.constants import DIMENSION_KEYS, SERVICE_NAME
from pctasks.server.request import ParsedRequest
from pctasks.server.settings import ServerSettings

logger = logging.getLogger(__name__)


PACKAGES = {
    SERVICE_NAME: "pctasks",
}


# Prevent successful health check pings from being logged
class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not record.args or len(record.args) != 5:
            return True

        args = cast(Tuple[str, str, str, str, int], record.args)
        endpoint = args[2]
        status = args[4]
        if endpoint.endswith("/_mgmt/ping") and status == 200:
            return False

        return True


# Custom filter that outputs custom_dimensions, only if present
class OptionalCustomDimensionsFilter(logging.Formatter):
    def __init__(
        self,
        message_fmt: Optional[str],
        dt_fmt: Optional[str],
        service_name: Optional[str],
    ):
        logging.Formatter.__init__(self, message_fmt, dt_fmt)
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        if "custom_dimensions" not in record.__dict__:
            record.__dict__["custom_dimensions"] = ""
        else:
            # Add the service name to custom_dimensions, so it's queryable
            record.__dict__["custom_dimensions"]["service"] = self.service_name
        return super().format(record)


# Log filter for Azure-targeted messages (containing custom_dimensions)
class CustomDimensionsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return bool(record.__dict__["custom_dimensions"])


# Initialize logging, including a console handler, and sending all logs containing
# custom_dimensions to Application Insights
def init_logging(service_name: str) -> None:
    settings = ServerSettings.get()

    # Exclude health check endpoint pings from the uvicorn logs
    logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

    # Setup logging
    log_level = logging.DEBUG if settings.dev else logging.INFO
    logger = logging.getLogger(pctasks.server.__name__)
    logger.setLevel(log_level)

    # Console log handler
    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setLevel(log_level)
    formatter = OptionalCustomDimensionsFilter(
        "[%(levelname)s] %(asctime)s - %(message)s %(custom_dimensions)s",
        None,
        service_name,
    )
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)

    # Azure log handler
    instrumentation_key = settings.app_insights_instrumentation_key
    if instrumentation_key:
        azure_handler = AzureLogHandler(
            connection_string=f"InstrumentationKey={instrumentation_key}"
        )
        azure_handler.addFilter(CustomDimensionsFilter())
        logger.addHandler(azure_handler)
    else:
        logger.info("Not adding Azure log handler since no instrumentation key defined")


def get_custom_dimensions(
    request: Union[Request, ParsedRequest], dimensions: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Merge the base dimensions with the given dimensions."""
    if isinstance(request, Request):
        request = ParsedRequest(request)

    base_dimensions: Dict[str, Optional[str]] = {
        **request.custom_dimensions,
    }

    if dimensions:
        base_dimensions.update(dimensions)

    return {"custom_dimensions": base_dimensions}


def log_request(
    parsed_request: ParsedRequest,
    msg: str,
    workflow_id: Optional[str] = None,
    run_id: Optional[str] = None,
    job_id: Optional[str] = None,
    partition_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> None:
    """Log the given request with the given status code."""
    route_dimensions: Dict[str, Any] = {}

    if workflow_id:
        route_dimensions[DIMENSION_KEYS.WORKFLOW_ID] = workflow_id
    if run_id:
        route_dimensions[DIMENSION_KEYS.RUN_ID] = run_id
    if job_id:
        route_dimensions[DIMENSION_KEYS.JOB_ID] = job_id
    if partition_id:
        route_dimensions[DIMENSION_KEYS.PARTITION_ID] = partition_id
    if task_id:
        route_dimensions[DIMENSION_KEYS.TASK_ID] = task_id

    logger.info(
        msg,
        extra=get_custom_dimensions(parsed_request, route_dimensions),
    )
