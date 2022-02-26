import os
from tempfile import TemporaryDirectory
from typing import List, Union

import pytest

from pctasks.cli.cli import pctasks_cmd
from pctasks.core.constants import (
    DEFAULT_LOG_CONTAINER,
    DEFAULT_SIGNAL_QUEUE_NAME,
    DEFAULT_TASK_IO_CONTAINER,
    DEFAULT_TASK_RUN_RECORD_TABLE_NAME,
)
from pctasks.core.models.base import PCBaseModel, RunRecordId
from pctasks.core.models.record import TaskRunRecord, TaskRunStatus
from pctasks.core.models.task import (
    FailedTaskResult,
    TaskRunConfig,
    TaskRunMessage,
    WaitTaskResult,
)
from pctasks.dev.config import get_blob_config, get_queue_config, get_table_config
from pctasks.dev.logs import get_log_storage
from pctasks.dev.tables import get_task_run_record_table
from pctasks.task.context import TaskContext
from pctasks.task.run import MissingEnvironmentError
from pctasks.task.task import Task


class MockTaskInput(PCBaseModel):
    result_path: str


class MockTaskOutput(PCBaseModel):
    message: str


class MockTask(Task[MockTaskInput, MockTaskOutput]):
    _input_model = MockTaskInput
    _output_model = MockTaskOutput

    def run(
        self, input: MockTaskInput, context: TaskContext
    ) -> Union[MockTaskOutput, WaitTaskResult, FailedTaskResult]:
        result_path = input.result_path
        with open(result_path, "w") as f:
            f.write("success")
        return MockTaskOutput(message="success")


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

    run_record_id = RunRecordId(
        job_id=job_id,
        task_id=task_id,
        run_id=run_id,
    )

    with get_task_run_record_table() as task_run_table:
        task_run_table.upsert_record(
            TaskRunRecord(
                run_id=run_id,
                job_id=job_id,
                task_id=task_id,
                status=TaskRunStatus.SUBMITTED,
            )
        )

        log_path = f"{job_id}/{task_id}/{run_id}.log"
        output_path = f"{job_id}/{task_id}/{run_id}-output.json"

        with TemporaryDirectory() as tmp_dir:
            msg = TaskRunMessage(
                args={"result_path": os.path.join(tmp_dir, "result.txt")},
                config=TaskRunConfig(
                    run_id=run_id,
                    job_id=job_id,
                    task_id=task_id,
                    signal_key="signal-key",
                    signal_target_id="target-id",
                    image="pctasks-task:latest",
                    task="tests.test_cli:mock_tasks.mock_task",
                    signal_queue=get_queue_config(DEFAULT_SIGNAL_QUEUE_NAME),
                    task_runs_table_config=get_table_config(
                        DEFAULT_TASK_RUN_RECORD_TABLE_NAME
                    ),
                    log_blob_config=get_blob_config(DEFAULT_LOG_CONTAINER, log_path),
                    output_blob_config=get_blob_config(
                        DEFAULT_TASK_IO_CONTAINER, output_path
                    ),
                ),
            )
            msg_path = os.path.join(tmp_dir, "testmsg.json")
            with open(msg_path, "w") as f:
                f.write(msg.encoded())

            pctasks_cmd.main(["task", "run", msg_path], standalone_mode=False)

            assert os.path.exists(msg.args["result_path"])
            with open(msg.args["result_path"]) as f:
                assert f.read() == "success"

        record = task_run_table.get_record(
            run_record_id=run_record_id,
        )
        assert record
        assert record.status == TaskRunStatus.COMPLETED


def test_task_func_fails_missing_env():

    job_id = "unit-test-job"
    task_id = "task-unit-test"
    run_id = "test_task_func_missing_env"

    run_record_id = RunRecordId(
        job_id=job_id,
        task_id=task_id,
        run_id=run_id,
    )

    with get_task_run_record_table() as task_run_table:
        task_run_table.upsert_record(
            TaskRunRecord(
                run_id=run_id,
                job_id=job_id,
                task_id=task_id,
                status=TaskRunStatus.SUBMITTED,
            )
        )

        log_path = f"unittests/{job_id}/{task_id}/{run_id}.log"
        output_path = f"{job_id}/{task_id}/{run_id}-output.json"

        with TemporaryDirectory() as tmp_dir:

            msg = TaskRunMessage(
                args={"result_path": os.path.join(tmp_dir, "result.txt")},
                config=TaskRunConfig(
                    run_id=run_id,
                    job_id=job_id,
                    task_id=task_id,
                    environment={},
                    signal_key="signal-key",
                    signal_target_id="target-id",
                    image="pctasks-task:latest",
                    task="tests.test_cli:mock_tasks.mock_task_require_env",
                    signal_queue=get_queue_config(DEFAULT_SIGNAL_QUEUE_NAME),
                    task_runs_table_config=get_table_config(
                        DEFAULT_TASK_RUN_RECORD_TABLE_NAME
                    ),
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

            log_storage = get_log_storage()
            logs = log_storage.read_text(log_path)
            assert "MissingEnvironmentError" in logs

        record = task_run_table.get_record(run_record_id=run_record_id)
        assert record
        assert record.status == TaskRunStatus.FAILED


def test_task_func_succeeds_env():
    job_id = "unit-test-job"
    task_id = "task-unit-test"
    run_id = "test_task_func"

    run_record_id = RunRecordId(
        job_id=job_id,
        task_id=task_id,
        run_id=run_id,
    )

    with get_task_run_record_table() as task_run_table:
        task_run_table.upsert_record(
            TaskRunRecord(
                run_id=run_id,
                job_id=job_id,
                task_id=task_id,
                status=TaskRunStatus.SUBMITTED,
            )
        )

        log_path = f"{job_id}/{task_id}/{run_id}.log"
        output_path = f"{job_id}/{task_id}/{run_id}-output.json"

        with TemporaryDirectory() as tmp_dir:
            msg = TaskRunMessage(
                args={"result_path": os.path.join(tmp_dir, "result.txt")},
                config=TaskRunConfig(
                    run_id=run_id,
                    job_id=job_id,
                    task_id=task_id,
                    signal_key="signal-key",
                    signal_target_id="target-id",
                    image="pctasks-task:latest",
                    task="tests.test_cli:mock_tasks.mock_task_require_env",
                    environment={"TEST_ENV_VAR": "yes"},
                    signal_queue=get_queue_config(DEFAULT_SIGNAL_QUEUE_NAME),
                    task_runs_table_config=get_table_config(
                        DEFAULT_TASK_RUN_RECORD_TABLE_NAME
                    ),
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

        record = task_run_table.get_record(
            run_record_id=run_record_id,
        )
        assert record
        assert record.status == TaskRunStatus.COMPLETED
