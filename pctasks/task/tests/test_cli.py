import os
from tempfile import TemporaryDirectory
from typing import List, Union

import pytest

from pctasks.cli.cli import pctasks_cmd
from pctasks.core.constants import DEFAULT_LOG_CONTAINER, DEFAULT_TASK_IO_CONTAINER
from pctasks.core.models.run import TaskRunStatus
from pctasks.core.models.task import (
    FailedTaskResult,
    TaskRunConfig,
    TaskRunMessage,
    WaitTaskResult,
)
from pctasks.core.storage.blob import BlobStorage, BlobUri
from pctasks.dev.blob import temp_azurite_blob_storage
from pctasks.dev.config import get_azurite_blob_config, get_blob_config
from pctasks.dev.logs import get_log_storage
from pctasks.dev.mocks import MockTask, MockTaskInput, MockTaskOutput
from pctasks.task.context import TaskContext
from pctasks.task.run import MissingEnvironmentError
from pctasks.task.task import Task


class MockTaskRequiredEnv(Task[MockTaskInput, MockTaskOutput]):
    _input_model = MockTaskInput
    _output_model = MockTaskOutput

    def get_required_environment_variables(self) -> List[str]:
        return ["TEST_ENV_VAR"]

    def run(
        self, input: MockTaskInput, context: TaskContext
    ) -> Union[MockTaskOutput, WaitTaskResult, FailedTaskResult]:
        result_path = input.result_path
        with open(result_path, "w") as f:
            f.write("success")
        return MockTaskOutput(message="success")


class MockTasks:
    mock_task = MockTask()
    mock_task_require_env = MockTaskRequiredEnv()


mock_tasks = MockTasks()


def test_task_func():
    job_id = "unit-test-job"
    task_id = "task-unit-test"
    run_id = "test_task_func"

    with temp_azurite_blob_storage() as storage:
        container_name = storage.container_name
        log_path = f"log/{job_id}/{task_id}/{run_id}.log"
        output_path = f"output/{job_id}/{task_id}/{run_id}-output.json"
        status_blob_config = get_azurite_blob_config(
            container_name, f"status/{job_id}/{task_id}/{run_id}-status.txt"
        )
        status_blob_storage = BlobStorage.from_uri(
            BlobUri(status_blob_config.uri).base_uri, status_blob_config.sas_token
        )
        status_path = status_blob_storage.get_path(status_blob_config.uri)

        with TemporaryDirectory() as tmp_dir:
            msg = TaskRunMessage(
                args={"result_path": os.path.join(tmp_dir, "result.txt")},
                config=TaskRunConfig(
                    run_id=run_id,
                    job_id=job_id,
                    partition_id="0",
                    task_id=task_id,
                    image="pctasks-task:latest",
                    task="tests.test_cli:mock_tasks.mock_task",
                    status_blob_config=status_blob_config,
                    log_blob_config=get_blob_config(container_name, log_path),
                    output_blob_config=get_blob_config(container_name, output_path),
                ),
            )
            msg_path = os.path.join(tmp_dir, "testmsg.json")
            with open(msg_path, "w") as f:
                f.write(msg.encoded())

            pctasks_cmd.main(["task", "run", msg_path], standalone_mode=False)

            assert status_blob_storage.file_exists(status_path)
            assert (
                TaskRunStatus(status_blob_storage.read_text(status_path))
                == TaskRunStatus.COMPLETING
            )

            assert os.path.exists(msg.args["result_path"])
            with open(msg.args["result_path"]) as f:
                assert f.read() == "success"


def test_task_func_fails_missing_env():

    job_id = "unit-test-job"
    task_id = "task-unit-test"
    run_id = "test_task_func_missing_env"

    with temp_azurite_blob_storage() as storage:
        container_name = storage.container_name

        log_path = f"unittests/{job_id}/{task_id}/{run_id}.log"
        output_path = f"{job_id}/{task_id}/{run_id}-output.json"
        status_blob_config = get_azurite_blob_config(
            container_name, f"status/{job_id}/{task_id}/{run_id}-status.json"
        )
        status_blob_storage = BlobStorage.from_uri(
            BlobUri(status_blob_config.uri).base_uri, status_blob_config.sas_token
        )
        status_path = status_blob_storage.get_path(status_blob_config.uri)

        with TemporaryDirectory() as tmp_dir:

            msg = TaskRunMessage(
                args={"result_path": os.path.join(tmp_dir, "result.txt")},
                config=TaskRunConfig(
                    run_id=run_id,
                    job_id=job_id,
                    partition_id="0",
                    task_id=task_id,
                    environment={},
                    image="pctasks-task:latest",
                    task="tests.test_cli:mock_tasks.mock_task_require_env",
                    status_blob_config=status_blob_config,
                    log_blob_config=get_blob_config(DEFAULT_LOG_CONTAINER, log_path),
                    output_blob_config=get_blob_config(
                        DEFAULT_TASK_IO_CONTAINER, output_path
                    ),
                ),
            )
            msg_path = os.path.join(tmp_dir, "testmsg.json")
            with open(msg_path, "w") as f:
                f.write(msg.encoded())

            with pytest.raises(MissingEnvironmentError):
                pctasks_cmd(["task", "run", msg_path], standalone_mode=False)

            assert status_blob_storage.file_exists(status_path)
            assert (
                TaskRunStatus(status_blob_storage.read_text(status_path))
                == TaskRunStatus.FAILED
            )

            log_storage = get_log_storage()
            logs = log_storage.read_text(log_path)
            assert "MissingEnvironmentError" in logs


def test_task_func_succeeds_env():
    job_id = "unit-test-job"
    task_id = "task-unit-test"
    run_id = "test_task_func"

    with temp_azurite_blob_storage() as storage:
        container_name = storage.container_name

        log_path = f"{job_id}/{task_id}/{run_id}.log"
        output_path = f"{job_id}/{task_id}/{run_id}-output.json"
        output_path = f"{job_id}/{task_id}/{run_id}-output.json"
        status_blob_config = get_azurite_blob_config(
            container_name, f"status/{job_id}/{task_id}/{run_id}-status.json"
        )
        status_blob_storage = BlobStorage.from_uri(
            BlobUri(status_blob_config.uri).base_uri, status_blob_config.sas_token
        )
        status_path = status_blob_storage.get_path(status_blob_config.uri)

        with TemporaryDirectory() as tmp_dir:
            msg = TaskRunMessage(
                args={"result_path": os.path.join(tmp_dir, "result.txt")},
                config=TaskRunConfig(
                    run_id=run_id,
                    job_id=job_id,
                    partition_id="0",
                    task_id=task_id,
                    image="pctasks-task:latest",
                    task="tests.test_cli:mock_tasks.mock_task_require_env",
                    environment={"TEST_ENV_VAR": "yes"},
                    status_blob_config=status_blob_config,
                    log_blob_config=get_blob_config(DEFAULT_LOG_CONTAINER, log_path),
                    output_blob_config=get_blob_config(
                        DEFAULT_TASK_IO_CONTAINER, output_path
                    ),
                ),
            )
            msg_path = os.path.join(tmp_dir, "testmsg.json")
            with open(msg_path, "w") as f:
                f.write(msg.encoded())

            pctasks_cmd(["task", "run", msg_path], standalone_mode=False)

            assert os.path.exists(msg.args["result_path"])
            with open(msg.args["result_path"]) as f:
                assert f.read() == "success"

            assert status_blob_storage.file_exists(status_path)
            assert (
                TaskRunStatus(status_blob_storage.read_text(status_path))
                == TaskRunStatus.COMPLETING
            )
