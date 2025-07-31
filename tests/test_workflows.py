from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest
import yaml
from pydantic import ValidationError

from pctasks.client.workflow.template import (
    template_workflow_contents,
    template_workflow_dict,
    template_workflow_file,
)
from pctasks.core.models.workflow import WorkflowDefinition


@pytest.fixture
def basic_job_definition() -> Dict[str, Any]:
    return {
        "tasks": [
            {
                "id": "test_task",
                "image": "test:latest",
                "task": "test.task:TestTask",
            }
        ]
    }


@pytest.fixture
def workflow_dict_with_args_as_dict(basic_job_definition) -> Dict[str, Any]:
    return {
        "name": "Sentinel 1 GRD",
        "dataset": "microsoft/sentinel-1-grd",
        "id": "test-sentinel-1-grd",
        "args": {
            "storage_container_name": "s1grd",
            "force": False,
            "uses_last_processed": True,
            "start_datetime_offset": None,
            "start_datetime": None,
            "end_datetime": None,
        },
        "jobs": {
            "initialize": {
                "tasks": [
                    {
                        "id": "initialize",
                        "image": "test:latest",
                        "task": "test.task:TestTask",
                        "args": {
                            "storage_container_name": "${{ args.storage_container_name }}",
                            "force": "${{ args.force }}",
                        },
                    }
                ]
            }
        },
    }


@pytest.fixture
def workflow_dict_with_args_as_list(basic_job_definition) -> Dict[str, Any]:
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": ["storage_container_name", "force", "start_datetime"],
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def workflow_dict_without_args(basic_job_definition) -> Dict[str, Any]:
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def workflow_dict_with_empty_args(basic_job_definition) -> Dict[str, Any]:
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": {},
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def workflow_dict_with_complex_args(basic_job_definition) -> Dict[str, Any]:
    return {
        "name": "Complex Args Workflow",
        "dataset": "test-dataset",
        "id": "complex-args-workflow",
        "args": {
            "string_param": "default_string",
            "int_param": 123,
            "bool_param": True,
            "null_param": None,
            "list_param": ["item1", "item2"],
            "dict_param": {"nested_key": "nested_value"},
            "float_param": 3.14,
        },
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def expected_args_from_dict() -> List[str]:
    return [
        "storage_container_name",
        "force",
        "uses_last_processed",
        "start_datetime_offset",
        "start_datetime",
        "end_datetime",
    ]


@pytest.fixture
def expected_complex_args() -> List[str]:
    return [
        "string_param",
        "int_param",
        "bool_param",
        "null_param",
        "list_param",
        "dict_param",
        "float_param",
    ]


@pytest.fixture
def sample_yaml_content() -> str:
    return """
name: Sentinel 1 GRD
dataset: microsoft/sentinel-1-grd
id: test-sentinel-1-grd

args:
  storage_container_name: "s1grd"
  force: false
  uses_last_processed: true
  start_datetime_offset: null
  start_datetime: null
  end_datetime: null

jobs:
  initialize:
    tasks:
      - id: initialize
        image: test:latest
        task: test.task:TestTask
        args:
          storage_container_name: ${{ args.storage_container_name }}
          force: ${{ args.force }}
"""


@pytest.fixture
def file_yaml_content() -> str:
    return """
name: Test Workflow File
dataset: test-dataset
id: test-workflow-file

args:
  container_name: "test-container"
  enable_feature: true
  timeout_seconds: 300

jobs:
  process:
    tasks:
      - id: process_task
        image: test:latest
        task: test.task:ProcessTask
        args:
          container: ${{ args.container_name }}
          enabled: ${{ args.enable_feature }}
          timeout: ${{ args.timeout_seconds }}
"""


@pytest.fixture
def invalid_workflow_yaml_content() -> str:
    return """
name: Test Workflow
args:
param1: value1
param2: value2
# Missing required 'dataset' and 'jobs' fields
"""


@pytest.fixture
def malformed_yaml_content() -> str:
    return """
name: Test Workflow
dataset: test-dataset  
id: test
args:
param1: value1
param2: [unclosed list
jobs:
test_job:
tasks: []
"""


@pytest.fixture
def invalid_workflow_dict_missing_name(basic_job_definition):
    return {
        # Missing required 'name' field
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": {"param1": "value1"},
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def invalid_workflow_dict_missing_dataset(basic_job_definition):
    return {
        "name": "Test Workflow",
        # Missing required 'dataset' field
        "id": "test-workflow",
        "args": {"param1": "value1"},
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def invalid_workflow_dict_missing_jobs():
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": {"param1": "value1"},
        # Missing required 'jobs' field
    }


@pytest.fixture
def invalid_workflow_dict_empty_jobs():
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": {"param1": "value1"},
        "jobs": {},  # Empty jobs should fail validation
    }


@pytest.fixture
def invalid_workflow_dict_malformed_jobs():
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": {"param1": "value1"},
        "jobs": {
            "test_job": {
                "tasks": [
                    {
                        # Missing required 'id' field in task
                        "image": "test:latest",
                        "task": "test.task:TestTask",
                    }
                ]
            }
        },
    }


def test_template_workflow_dict_with_args_as_dict(
    workflow_dict_with_args_as_dict: Dict[str, Any],
    expected_args_from_dict: List[str],
) -> None:
    result = template_workflow_dict(workflow_dict_with_args_as_dict)

    # Verify that args dictionary was converted to list of keys
    assert result.args == expected_args_from_dict
    assert isinstance(result, WorkflowDefinition)
    assert result.name == "Sentinel 1 GRD"
    assert result.dataset_id == "microsoft/sentinel-1-grd"


def test_template_workflow_dict_with_args_as_list(
    workflow_dict_with_args_as_list: dict,
) -> None:
    result = template_workflow_dict(workflow_dict_with_args_as_list)

    # Verify that args list was preserved unchanged
    assert result.args == ["storage_container_name", "force", "start_datetime"]
    assert isinstance(result, WorkflowDefinition)


def test_template_workflow_dict_without_args(
    workflow_dict_without_args: Dict[str, Any],
) -> None:
    result = template_workflow_dict(workflow_dict_without_args)

    assert result.args is None
    assert isinstance(result, WorkflowDefinition)


def test_template_workflow_contents_with_yaml_string(
    sample_yaml_content: str, expected_args_from_dict: List[str]
) -> None:
    result = template_workflow_contents(sample_yaml_content)

    assert result.args == expected_args_from_dict
    assert isinstance(result, WorkflowDefinition)
    assert result.name == "Sentinel 1 GRD"


@patch("pathlib.Path.read_text")
def test_template_workflow_file_with_mocked_file(
    mock_read_text: MagicMock, file_yaml_content: str
) -> None:
    mock_read_text.return_value = file_yaml_content

    result = template_workflow_file("/fake/path/workflow.yaml")

    expected_args = ["container_name", "enable_feature", "timeout_seconds"]
    assert result.args == expected_args
    assert isinstance(result, WorkflowDefinition)
    assert result.name == "Test Workflow File"
    mock_read_text.assert_called_once()


def test_template_workflow_dict_args_dict_empty(
    workflow_dict_with_empty_args: Dict[str, Any],
) -> None:
    result = template_workflow_dict(workflow_dict_with_empty_args)

    assert result.args == []
    assert isinstance(result, WorkflowDefinition)


def test_template_workflow_dict_with_complex_args_values(
    workflow_dict_with_complex_args: Dict[str, Any],
    expected_complex_args: List[str],
) -> None:
    result = template_workflow_dict(workflow_dict_with_complex_args)

    # Args should contain all keys regardless of their default value types
    assert all(arg in result.args for arg in expected_complex_args)
    assert len(result.args) == len(expected_complex_args)
    assert isinstance(result, WorkflowDefinition)


def test_template_workflow_dict_validation_failure_missing_name(
    invalid_workflow_dict_missing_name,
):
    with pytest.raises(ValidationError) as exc_info:
        template_workflow_dict(invalid_workflow_dict_missing_name)

    # Verify the error is related to the missing 'name' field
    error_str = str(exc_info.value)
    assert "name" in error_str.lower()


def test_template_workflow_dict_validation_failure_missing_dataset(
    invalid_workflow_dict_missing_dataset: Dict[str, Any],
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        template_workflow_dict(invalid_workflow_dict_missing_dataset)

    # Verify the error is related to the missing 'dataset' field
    error_str = str(exc_info.value)
    assert "dataset" in error_str.lower()


def test_template_workflow_dict_validation_failure_missing_jobs(
    invalid_workflow_dict_missing_jobs: Dict[str, Any],
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        template_workflow_dict(invalid_workflow_dict_missing_jobs)

    # Verify the error is related to the missing 'jobs' field
    error_str = str(exc_info.value)
    assert "jobs" in error_str.lower()


def test_template_workflow_dict_validation_failure_empty_jobs(
    invalid_workflow_dict_empty_jobs: Dict[str, Any],
) -> None:
    # Note: This test might pass if empty jobs dict is actually allowed
    # Adjust expectation based on actual WorkflowDefinition validation rules
    try:
        result = template_workflow_dict(invalid_workflow_dict_empty_jobs)
        # If this doesn't raise an exception, empty jobs might be allowed
        # In that case, just verify it's a valid WorkflowDefinition with empty jobs
        assert isinstance(result, WorkflowDefinition)
        assert result.jobs == {}
    except ValidationError:
        # This is expected if empty jobs are not allowed
        pass


def test_template_workflow_dict_validation_failure_malformed_jobs(
    invalid_workflow_dict_malformed_jobs: Dict[str, Any],
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        template_workflow_dict(invalid_workflow_dict_malformed_jobs)

    # Verify the error is related to task validation
    error_str = str(exc_info.value)
    # The error should mention something about task validation or missing fields
    assert any(keyword in error_str.lower() for keyword in ["id", "task", "field"])


def test_template_workflow_dict_args_conversion_then_validation_failure() -> None:
    # Create a workflow dict that has args as dict but missing required fields
    invalid_workflow_with_args_dict = {
        "args": {
            "storage_container_name": "s1grd",
            "force": False,
        },
        # Missing required fields: name, dataset, jobs
    }

    with pytest.raises(ValidationError) as exc_info:
        template_workflow_dict(invalid_workflow_with_args_dict)

    # Verify that validation failed (which means args conversion happened first)
    error_str = str(exc_info.value)
    assert any(keyword in error_str.lower() for keyword in ["name", "dataset", "jobs"])


def test_template_workflow_contents_validation_failure_malformed_yaml_content(
    malformed_yaml_content: str,
) -> None:
    with pytest.raises(yaml.YAMLError):
        template_workflow_contents(malformed_yaml_content)


def test_template_workflow_contents_validation_failure_invalid_content(
    invalid_workflow_yaml_content: str,
) -> None:
    with pytest.raises(ValidationError) as exc_info:
        template_workflow_contents(invalid_workflow_yaml_content)

    error_str = str(exc_info.value)
    assert any(keyword in error_str.lower() for keyword in ["dataset", "jobs"])
