import logging
from datetime import datetime, timezone
from typing import List, Union

from azure.identity import DefaultAzureCredential
from azure.monitor.query import (
    LogsQueryClient,
    LogsQueryError,
    LogsQueryPartialResult,
    LogsQueryResult,
    LogsQueryStatus,
    LogsTable,
    LogsTableRow,
)

logger = logging.getLogger(__name__)


class QueryError(Exception):
    pass


def query_logs(
    query: str, start_time: datetime, end_time: datetime, workspace_id: str
) -> List[LogsTableRow]:
    credential = DefaultAzureCredential()
    with LogsQueryClient(credential) as client:
        response: Union[
            LogsQueryResult, LogsQueryPartialResult
        ] = client.query_workspace(
            workspace_id=workspace_id,
            query=query,
            timespan=(
                start_time.replace(tzinfo=timezone.utc),
                end_time.replace(tzinfo=timezone.utc),
            ),
        )
        if isinstance(response, LogsQueryPartialResult):
            error: LogsQueryError = response.partial_error  # type: ignore
            data: List[LogsTable] = response.partial_data  # type: ignore
            raise QueryError(error.message)
        elif response.status == LogsQueryStatus.SUCCESS:
            data: List[LogsTable] = response.tables  # type: ignore
        else:
            raise QueryError("Unknown response")
        table = data[0]
        return table.rows
