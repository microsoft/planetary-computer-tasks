from typing import Generator
from unittest.mock import Mock, patch

import msrest.exceptions
import pytest
from azure.batch.custom.custom_errors import CreateTasksErrorException
from azure.batch.models import BatchError, BatchErrorDetail, ErrorMessage, TaskAddResult

from pctasks.run.batch.client import BatchClient
from pctasks.run.batch.task import BatchTask
from pctasks.run.settings import BatchSettings


class CustomExceptionWithMessage(Exception):
    """Custom exception with message attribute for testing."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


@pytest.fixture
def mock_settings() -> Mock:
    mock_settings = Mock(spec=BatchSettings)
    mock_settings.url = "https://test.batch.azure.com"
    mock_settings.key = "test_key"
    mock_settings.default_pool_id = "test_pool"
    mock_settings.submit_threads = 4
    mock_settings.cache_seconds = 5
    mock_settings.get_batch_name = Mock(return_value="test")
    return mock_settings


@pytest.fixture
def batch_client(mock_settings: Mock) -> BatchClient:
    client = BatchClient(mock_settings)
    return client


@pytest.fixture
def mock_batch_service_client(batch_client: BatchClient) -> Generator[Mock, None, None]:
    mock_client = Mock()
    with patch.object(batch_client, "_ensure_client", return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_task(mock_batch_service_client: Mock) -> Mock:
    mock_task_api = Mock()
    mock_batch_service_client.task = mock_task_api
    return mock_task_api


@pytest.fixture
def mock_error() -> Mock:
    error = Mock(spec=BatchError)
    error.code = "test_error"
    error.message = None
    error.values = None
    return error


@pytest.fixture
def mock_task_add_result(mock_error: Mock) -> Mock:
    result = Mock(spec=TaskAddResult)
    result.error = mock_error
    result.task_id = "test-task-id"
    return result


@pytest.fixture
def create_tasks_exception(mock_task_add_result: Mock) -> CreateTasksErrorException:
    return CreateTasksErrorException(
        "ClientError",
        errors=[],
        failure_tasks=[mock_task_add_result],
    )


@pytest.fixture
def mock_tasks() -> list[Mock]:
    tasks = [Mock(spec=BatchTask) for _ in range(3)]
    for task in tasks:
        task.to_params = Mock(return_value={})
    return tasks


def test_add_collection_handles_missing_message(
    batch_client: BatchClient,
    mock_task: Mock,
    create_tasks_exception: CreateTasksErrorException,
    mock_tasks: list[Mock],
) -> None:
    mock_task.add_collection.side_effect = create_tasks_exception
    with pytest.raises(CreateTasksErrorException) as excinfo:
        batch_client.add_collection("test-job-id", mock_tasks)

    assert excinfo.value is create_tasks_exception


@pytest.mark.parametrize(
    "error_type, error_args, expected_code, expected_message",
    [
        (
            BatchError,
            {
                "code": "BatchErrorCode",
                "message": ErrorMessage(value="Batch error message"),
            },
            "BatchErrorCode",
            "Batch error message",
        ),
        (
            msrest.exceptions.ClientRequestError,
            ["Client request failed"],
            "ClientRequestError",
            "Client request failed",
        ),
        (ValueError, ["Invalid value"], "ValueError", "Invalid value"),
        (
            CustomExceptionWithMessage,
            ["Custom error message"],
            "CustomExceptionWithMessage",
            "Custom error message",
        ),
        (Exception, [], "Exception", ""),
        (
            BatchError,
            {
                "code": "ValueError",
                "message": ErrorMessage(value="Error with details"),
                "values": [BatchErrorDetail(key="detail1", value="value1")],
            },
            "ValueError",
            "Error with details",
        ),
    ],
)
def test_to_batch_error_conversion(
    batch_client: BatchClient,
    error_type: type,
    error_args: list,
    expected_code: str,
    expected_message: str,
) -> None:
    if isinstance(error_args, dict):
        error = error_type(**error_args)
    else:
        error = error_type(*error_args)

    batch_error = batch_client._to_batch_error(error)

    assert batch_error.code == expected_code

    if hasattr(batch_error.message, "value"):
        assert batch_error.message.value == expected_message
    else:
        assert str(batch_error.message) == expected_message

    if hasattr(error, "values") and error.values:
        assert batch_error.values == error.values


def test_add_collection_handles_different_error_types(
    batch_client: BatchClient,
    mock_task: Mock,
    mock_tasks: list[Mock],
) -> None:
    client_request_error = msrest.exceptions.ClientRequestError("Network failure")

    batch_error = BatchError(
        code="BatchErrorCode", message=ErrorMessage(value="Batch processing error")
    )

    task_result1 = Mock(spec=TaskAddResult)
    task_result1.task_id = "task-1"
    task_result1.error = client_request_error

    task_result2 = Mock(spec=TaskAddResult)
    task_result2.task_id = "task-2"
    task_result2.error = batch_error

    mixed_exception = CreateTasksErrorException(
        pending_tasks=[],
        failure_tasks=[task_result1, task_result2],
        errors=[ValueError("Another error")],
    )

    mock_task.add_collection.side_effect = mixed_exception

    with pytest.raises(CreateTasksErrorException) as excinfo:
        batch_client.add_collection("test-job-id", mock_tasks)

    assert excinfo.value is mixed_exception
