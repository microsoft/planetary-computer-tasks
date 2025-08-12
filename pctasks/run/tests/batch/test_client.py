from unittest.mock import Mock

import pytest
from azure.batch.custom.custom_errors import CreateTasksErrorException
from azure.batch.models import BatchError, TaskAddResult

from pctasks.run.batch.client import BatchClient
from pctasks.run.batch.task import BatchTask
from pctasks.run.settings import BatchSettings


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
def mock_batch_service_client(batch_client: BatchClient) -> Mock:
    mock_client = Mock()
    batch_client._ensure_client = Mock(return_value=mock_client)
    return mock_client


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
    batch_client._with_backoff = lambda func, is_throttle=None: func()
    with pytest.raises(CreateTasksErrorException) as excinfo:
        batch_client.add_collection("test-job-id", mock_tasks)

    assert excinfo.value is create_tasks_exception
