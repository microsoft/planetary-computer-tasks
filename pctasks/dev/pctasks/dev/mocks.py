from typing import Union

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.task.context import TaskContext
from pctasks.task.task import Task


class MockTaskContext(TaskContext):
    """Mock TaskContext for use in task tests."""

    @classmethod
    def default(cls) -> "MockTaskContext":
        return MockTaskContext(storage_factory=StorageFactory(), run_id="run-id")


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
