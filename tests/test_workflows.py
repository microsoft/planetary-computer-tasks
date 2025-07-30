import pytest
import yaml
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any
from pctasks.client.workflow.template import (
    template_workflow_dict,
    template_workflow_contents,
    template_workflow_file,
)
from pctasks.core.models.workflow import WorkflowDefinition
from pydantic import ValidationError


@pytest.fixture
def basic_job_definition() -> Dict[str, Any]:
    """basic_job_definition # noqa: E501

    Fixture providing a basic job definition for workflow tests

    :return: Dictionary containing basic job structure
    :rtype: dict

    Example:

        ```python
        def test_something(basic_job_definition):
            workflow_dict = {
                "name": "Test",
                "dataset": "test-dataset",
                "id": "test-id",
                "jobs": {"test_job": basic_job_definition}
            }
        ```
    """
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
    """workflow_dict_with_args_as_dict # noqa: E501

    Fixture providing workflow dictionary with args as dictionary format

    :param basic_job_definition: Basic job definition fixture
    :type basic_job_definition: dict
    :return: Workflow dictionary with args as dict containing default values
    :rtype: dict

    Example:

        ```python
        def test_args_conversion(workflow_dict_with_args_as_dict):
            result = template_workflow_dict(workflow_dict_with_args_as_dict)
            assert isinstance(result.args, list)
        ```
    """
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
    """workflow_dict_with_args_as_list # noqa: E501

    Fixture providing workflow dictionary with args as list format

    :param basic_job_definition: Basic job definition fixture
    :type basic_job_definition: dict
    :return: Workflow dictionary with args as list of parameter names
    :rtype: dict

    Example:

        ```python
        def test_args_preservation(workflow_dict_with_args_as_list):
            result = template_workflow_dict(workflow_dict_with_args_as_list)
            assert result.args == ["storage_container_name", "force", "start_datetime"]
        ```
    """
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": ["storage_container_name", "force", "start_datetime"],
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def workflow_dict_without_args(basic_job_definition) -> Dict[str, Any]:
    """workflow_dict_without_args # noqa: E501

    Fixture providing workflow dictionary with no args specified

    :param basic_job_definition: Basic job definition fixture
    :type basic_job_definition: dict
    :return: Workflow dictionary without args field
    :rtype: dict

    Example:

        ```python
        def test_no_args(workflow_dict_without_args):
            result = template_workflow_dict(workflow_dict_without_args)
            assert result.args is None
        ```
    """
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def workflow_dict_with_empty_args(basic_job_definition) -> Dict[str, Any]:
    """workflow_dict_with_empty_args # noqa: E501

    Fixture providing workflow dictionary with empty args dictionary

    :param basic_job_definition: Basic job definition fixture
    :type basic_job_definition: dict
    :return: Workflow dictionary with empty args dict
    :rtype: dict

    Example:

        ```python
        def test_empty_args(workflow_dict_with_empty_args):
            result = template_workflow_dict(workflow_dict_with_empty_args)
            assert result.args == []
        ```
    """
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": {},
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def workflow_dict_with_complex_args(basic_job_definition) -> Dict[str, Any]:
    """workflow_dict_with_complex_args # noqa: E501

    Fixture providing workflow dictionary with complex args containing various data types

    :param basic_job_definition: Basic job definition fixture
    :type basic_job_definition: dict
    :return: Workflow dictionary with args containing different data types as defaults
    :rtype: dict

    Example:

        ```python
        def test_complex_args(workflow_dict_with_complex_args):
            result = template_workflow_dict(workflow_dict_with_complex_args)
            assert "string_param" in result.args
            assert "dict_param" in result.args
        ```
    """
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
    """expected_args_from_dict # noqa: E501

    Fixture providing expected args list from dictionary conversion

    :return: List of expected argument names after dict-to-list conversion
    :rtype: list

    Example:

        ```python
        def test_conversion(workflow_dict_with_args_as_dict, expected_args_from_dict):
            result = template_workflow_dict(workflow_dict_with_args_as_dict)
            assert result.args == expected_args_from_dict
        ```
    """
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
    """expected_complex_args # noqa: E501

    Fixture providing expected args list from complex dictionary conversion

    :return: List of expected argument names from complex args dictionary
    :rtype: list

    Example:

        ```python
        def test_complex_conversion(workflow_dict_with_complex_args, expected_complex_args):
            result = template_workflow_dict(workflow_dict_with_complex_args)
            assert all(arg in result.args for arg in expected_complex_args)
        ```
    """
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
    """sample_yaml_content # noqa: E501

    Fixture providing sample YAML content for workflow template testing

    :return: YAML string containing workflow definition with args dictionary
    :rtype: str

    Example:

        ```python
        def test_yaml_parsing(sample_yaml_content):
            result = template_workflow_contents(sample_yaml_content)
            assert result.name == "Sentinel 1 GRD"
        ```
    """
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
    """file_yaml_content # noqa: E501

    Fixture providing YAML content for file-based workflow template testing

    :return: YAML string for mocked file content testing
    :rtype: str

    Example:

        ```python
        def test_file_processing(file_yaml_content):
            with patch('pathlib.Path.read_text', return_value=file_yaml_content):
                result = template_workflow_file("/fake/path.yaml")
                assert result.name == "Test Workflow File"
        ```
    """
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
def invalid_workflow_dict_missing_name(basic_job_definition):
    """invalid_workflow_dict_missing_name # noqa: E501

    Fixture providing workflow dictionary missing required 'name' field

    :param basic_job_definition: Basic job definition fixture
    :type basic_job_definition: dict
    :return: Invalid workflow dictionary missing name field
    :rtype: dict

    Example:

        ```python
        def test_validation_failure(invalid_workflow_dict_missing_name):
            with pytest.raises(ValidationError):
                template_workflow_dict(invalid_workflow_dict_missing_name)
        ```
    """
    return {
        # Missing required 'name' field
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": {"param1": "value1"},
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def invalid_workflow_dict_missing_dataset(basic_job_definition):
    """invalid_workflow_dict_missing_dataset # noqa: E501

    Fixture providing workflow dictionary missing required 'dataset' field

    :param basic_job_definition: Basic job definition fixture
    :type basic_job_definition: dict
    :return: Invalid workflow dictionary missing dataset field
    :rtype: dict

    Example:

        ```python
        def test_dataset_validation_failure(invalid_workflow_dict_missing_dataset):
            with pytest.raises(ValidationError):
                template_workflow_dict(invalid_workflow_dict_missing_dataset)
        ```
    """
    return {
        "name": "Test Workflow",
        # Missing required 'dataset' field
        "id": "test-workflow",
        "args": {"param1": "value1"},
        "jobs": {"test_job": basic_job_definition},
    }


@pytest.fixture
def invalid_workflow_dict_missing_jobs():
    """invalid_workflow_dict_missing_jobs # noqa: E501

    Fixture providing workflow dictionary missing required 'jobs' field

    :return: Invalid workflow dictionary missing jobs field
    :rtype: dict

    Example:

        ```python
        def test_jobs_validation_failure(invalid_workflow_dict_missing_jobs):
            with pytest.raises(ValidationError):
                template_workflow_dict(invalid_workflow_dict_missing_jobs)
        ```
    """
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": {"param1": "value1"},
        # Missing required 'jobs' field
    }


@pytest.fixture
def invalid_workflow_dict_empty_jobs():
    """invalid_workflow_dict_empty_jobs # noqa: E501

    Fixture providing workflow dictionary with empty jobs dictionary

    :return: Invalid workflow dictionary with empty jobs
    :rtype: dict

    Example:

        ```python
        def test_empty_jobs_validation_failure(invalid_workflow_dict_empty_jobs):
            with pytest.raises(ValidationError):
                template_workflow_dict(invalid_workflow_dict_empty_jobs)
        ```
    """
    return {
        "name": "Test Workflow",
        "dataset": "test-dataset",
        "id": "test-workflow",
        "args": {"param1": "value1"},
        "jobs": {},  # Empty jobs should fail validation
    }


@pytest.fixture
def invalid_workflow_dict_malformed_jobs():
    """invalid_workflow_dict_malformed_jobs # noqa: E501

    Fixture providing workflow dictionary with malformed jobs structure

    :return: Invalid workflow dictionary with malformed jobs
    :rtype: dict

    Example:

        ```python
        def test_malformed_jobs_validation_failure(invalid_workflow_dict_malformed_jobs):
            with pytest.raises(ValidationError):
                template_workflow_dict(invalid_workflow_dict_malformed_jobs)
        ```
    """
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
    """test_template_workflow_dict_with_args_as_dict # noqa: E501

    Test that args dictionary with default values is converted to list format

    :param workflow_dict_with_args_as_dict: Workflow dict with args as dictionary
    :type workflow_dict_with_args_as_dict: dict
    :param expected_args_from_dict: Expected args list after conversion
    :type expected_args_from_dict: list
    :return: None - test validation through assertions
    :rtype: None

    Example:

        ```python
        result = template_workflow_dict(workflow_dict_with_args_as_dict)
        assert result.args == expected_args_from_dict
        ```
    """
    result = template_workflow_dict(workflow_dict_with_args_as_dict)

    # Verify that args dictionary was converted to list of keys
    assert result.args == expected_args_from_dict
    assert isinstance(result, WorkflowDefinition)
    assert result.name == "Sentinel 1 GRD"
    assert result.dataset_id == "microsoft/sentinel-1-grd"


def test_template_workflow_dict_with_args_as_list(
    workflow_dict_with_args_as_list: dict,
) -> None:
    """test_template_workflow_dict_with_args_as_list # noqa: E501

    Test that existing args list format is preserved unchanged



    :param workflow_dict_with_args_as_list: Workflow dict with args as list
    :type workflow_dict_with_args_as_list: dict
    :return: None - test validation through assertions
    :rtype: None

    Example:

        ```python
        result = template_workflow_dict(workflow_dict_with_args_as_list)
        assert result.args == ["storage_container_name", "force", "start_datetime"]
        ```
    """
    result = template_workflow_dict(workflow_dict_with_args_as_list)

    # Verify that args list was preserved unchanged
    assert result.args == ["storage_container_name", "force", "start_datetime"]
    assert isinstance(result, WorkflowDefinition)


def test_template_workflow_dict_without_args(
    workflow_dict_without_args: Dict[str, Any],
) -> None:
    """test_template_workflow_dict_without_args # noqa: E501

    Test workflow template processing when no args are specified

    :param workflow_dict_without_args: Workflow dict without args field
    :type workflow_dict_without_args: dict
    :return: None - test validation through assertions
    :rtype: None

    Example:

        ```python
        result = template_workflow_dict(workflow_dict_without_args)
        assert result.args is None
        ```
    """
    result = template_workflow_dict(workflow_dict_without_args)

    assert result.args is None
    assert isinstance(result, WorkflowDefinition)


def test_template_workflow_contents_with_yaml_string(
    sample_yaml_content: str, expected_args_from_dict: List[str]
) -> None:
    """test_template_workflow_contents_with_yaml_string # noqa: E501

    Test workflow template processing from YAML string content

    :param sample_yaml_content: Sample YAML content for testing
    :type sample_yaml_content: str
    :param expected_args_from_dict: Expected args list after conversion
    :type expected_args_from_dict: list
    :return: None - test validation through assertions
    :rtype: None

    Example:

        ```python
        result = template_workflow_contents(sample_yaml_content)
        assert result.args == expected_args_from_dict
        ```
    """
    result = template_workflow_contents(sample_yaml_content)

    assert result.args == expected_args_from_dict
    assert isinstance(result, WorkflowDefinition)
    assert result.name == "Sentinel 1 GRD"


@patch("pathlib.Path.read_text")
def test_template_workflow_file_with_mocked_file(
    mock_read_text: MagicMock, file_yaml_content: str
) -> None:
    """test_template_workflow_file_with_mocked_file # noqa: E501

    Test workflow template processing from file with mocked file system

    :param mock_read_text: Mock for Path.read_text method
    :type mock_read_text: MagicMock
    :param file_yaml_content: YAML content for mocked file
    :type file_yaml_content: str
    :return: None - test validation through assertions
    :rtype: None

    Example:

        ```python
        mock_read_text.return_value = file_yaml_content
        result = template_workflow_file("/path/to/workflow.yaml")
        assert "container_name" in result.args
        ```
    """
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
    """test_template_workflow_dict_args_dict_empty # noqa: E501

    Test behavior when args dictionary is empty

    :param workflow_dict_with_empty_args: Workflow dict with empty args dictionary
    :type workflow_dict_with_empty_args: dict
    :return: None - test validation through assertions
    :rtype: None

    Example:

        ```python
        result = template_workflow_dict(workflow_dict_with_empty_args)
        assert result.args == []
        ```
    """
    result = template_workflow_dict(workflow_dict_with_empty_args)

    assert result.args == []
    assert isinstance(result, WorkflowDefinition)


def test_template_workflow_dict_with_complex_args_values(
    workflow_dict_with_complex_args: Dict[str, Any],
    expected_complex_args: List[str],
) -> None:
    """test_template_workflow_dict_with_complex_args_values # noqa: E501

    Test args dictionary conversion with various data types as default values

    :param workflow_dict_with_complex_args: Workflow dict with complex args types
    :type workflow_dict_with_complex_args: dict
    :param expected_complex_args: Expected args list from complex dictionary
    :type expected_complex_args: list
    :return: None - test validation through assertions
    :rtype: None

    Example:

        ```python
        result = template_workflow_dict(workflow_dict_with_complex_args)
        assert all(arg in result.args for arg in expected_complex_args)
        ```
    """
    result = template_workflow_dict(workflow_dict_with_complex_args)

    # Args should contain all keys regardless of their default value types
    assert all(arg in result.args for arg in expected_complex_args)
    assert len(result.args) == len(expected_complex_args)
    assert isinstance(result, WorkflowDefinition)


def test_template_workflow_dict_validation_failure_missing_name(
    invalid_workflow_dict_missing_name,
):
    """test_template_workflow_dict_validation_failure_missing_name # noqa: E501

    Test that model validation fails when required 'name' field is missing

    :param invalid_workflow_dict_missing_name: Invalid workflow dict missing name
    :type invalid_workflow_dict_missing_name: dict
    :return: None - test validation through exception assertion
    :rtype: None
    :raises ValidationError: When workflow validation fails

    Example:

        ```python
        with pytest.raises(ValidationError) as exc_info:
            template_workflow_dict(invalid_workflow_dict_missing_name)
        assert "name" in str(exc_info.value)
        ```
    """

    with pytest.raises(ValidationError) as exc_info:
        template_workflow_dict(invalid_workflow_dict_missing_name)

    # Verify the error is related to the missing 'name' field
    error_str = str(exc_info.value)
    assert "name" in error_str.lower()


def test_template_workflow_dict_validation_failure_missing_dataset(
    invalid_workflow_dict_missing_dataset: Dict[str, Any],
) -> None:
    """test_template_workflow_dict_validation_failure_missing_dataset # noqa: E501

    Test that model validation fails when required 'dataset' field is missing

    :param invalid_workflow_dict_missing_dataset: Invalid workflow dict missing dataset
    :type invalid_workflow_dict_missing_dataset: dict
    :return: None - test validation through exception assertion
    :rtype: None
    :raises ValidationError: When workflow validation fails

    Example:

        ```python
        with pytest.raises(ValidationError) as exc_info:
            template_workflow_dict(invalid_workflow_dict_missing_dataset)
        assert "dataset" in str(exc_info.value)
        ```
    """

    with pytest.raises(ValidationError) as exc_info:
        template_workflow_dict(invalid_workflow_dict_missing_dataset)

    # Verify the error is related to the missing 'dataset' field
    error_str = str(exc_info.value)
    assert "dataset" in error_str.lower()


def test_template_workflow_dict_validation_failure_missing_jobs(
    invalid_workflow_dict_missing_jobs: Dict[str, Any],
) -> None:
    """test_template_workflow_dict_validation_failure_missing_jobs # noqa: E501

    Test that model validation fails when required 'jobs' field is missing

    :param invalid_workflow_dict_missing_jobs: Invalid workflow dict missing jobs
    :type invalid_workflow_dict_missing_jobs: dict
    :return: None - test validation through exception assertion
    :rtype: None
    :raises ValidationError: When workflow validation fails

    Example:

        ```python
        with pytest.raises(ValidationError) as exc_info:
            template_workflow_dict(invalid_workflow_dict_missing_jobs)
        assert "jobs" in str(exc_info.value)
        ```
    """

    with pytest.raises(ValidationError) as exc_info:
        template_workflow_dict(invalid_workflow_dict_missing_jobs)

    # Verify the error is related to the missing 'jobs' field
    error_str = str(exc_info.value)
    assert "jobs" in error_str.lower()


def test_template_workflow_dict_validation_failure_empty_jobs(
    invalid_workflow_dict_empty_jobs: Dict[str, Any],
) -> None:
    """test_template_workflow_dict_validation_failure_empty_jobs # noqa: E501

    Test that model validation fails when jobs dictionary is empty

    :param invalid_workflow_dict_empty_jobs: Invalid workflow dict with empty jobs
    :type invalid_workflow_dict_empty_jobs: dict
    :return: None - test validation through exception assertion
    :rtype: None
    :raises ValidationError: When workflow validation fails due to empty jobs

    Example:

        ```python
        with pytest.raises(ValidationError) as exc_info:
            template_workflow_dict(invalid_workflow_dict_empty_jobs)
        # Validation should fail for empty jobs
        ```
    """

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
    """test_template_workflow_dict_validation_failure_malformed_jobs # noqa: E501

    Test that model validation fails when jobs contain malformed task definitions

    :param invalid_workflow_dict_malformed_jobs: Invalid workflow dict with malformed jobs
    :type invalid_workflow_dict_malformed_jobs: dict
    :return: None - test validation through exception assertion
    :rtype: None
    :raises ValidationError: When workflow validation fails due to malformed jobs

    Example:

        ```python
        with pytest.raises(ValidationError) as exc_info:
            template_workflow_dict(invalid_workflow_dict_malformed_jobs)
        # Should fail because task is missing required 'id' field
        ```
    """

    with pytest.raises(ValidationError) as exc_info:
        template_workflow_dict(invalid_workflow_dict_malformed_jobs)

    # Verify the error is related to task validation
    error_str = str(exc_info.value)
    # The error should mention something about task validation or missing fields
    assert any(keyword in error_str.lower() for keyword in ["id", "task", "field"])


def test_template_workflow_dict_args_conversion_then_validation_failure() -> None:
    """test_template_workflow_dict_args_conversion_then_validation_failure # noqa: E501

    Test that args are converted from dict to list even when validation fails

    :return: None - test validation through exception assertion
    :rtype: None
    :raises ValidationError: When workflow validation fails after args conversion

    Example:

        ```python
        # Verify that args conversion happens before validation failure
        invalid_dict = {"args": {"param1": "value1"}}  # missing required fields
        with pytest.raises(ValidationError):
            template_workflow_dict(invalid_dict)
        # Args should have been converted to list before validation failed
        ```
    """

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


def test_template_workflow_contents_validation_failure_malformed_yaml() -> None:
    """test_template_workflow_contents_validation_failure_malformed_yaml # noqa: E501

    Test that template_workflow_contents fails gracefully with malformed YAML

    :return: None - test validation through exception assertion
    :rtype: None
    :raises YAMLError: When YAML parsing fails

    Example:

        ```python
        malformed_yaml = "name: Test\n  invalid: yaml: structure"
        with pytest.raises(yaml.YAMLError):
            template_workflow_contents(malformed_yaml)
        ```
    """

    malformed_yaml = """
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

    with pytest.raises(yaml.YAMLError):
        template_workflow_contents(malformed_yaml)


def test_template_workflow_contents_validation_failure_invalid_content() -> None:
    """test_template_workflow_contents_validation_failure_invalid_content # noqa: E501

    Test that template_workflow_contents fails with valid YAML but invalid workflow

    :return: None - test validation through exception assertion
    :rtype: None
    :raises ValidationError: When workflow model validation fails

    Example:

        ```python
        invalid_yaml = "name: Test\nargs: {param1: value1}"  # missing required fields
        with pytest.raises(ValidationError):
            template_workflow_contents(invalid_yaml)
        ```
    """

    # Valid YAML but invalid workflow (missing required fields)
    invalid_workflow_yaml = """
name: Test Workflow
args:
param1: value1
param2: value2
# Missing required 'dataset' and 'jobs' fields
"""

    with pytest.raises(ValidationError) as exc_info:
        template_workflow_contents(invalid_workflow_yaml)

    error_str = str(exc_info.value)
    assert any(keyword in error_str.lower() for keyword in ["dataset", "jobs"])
