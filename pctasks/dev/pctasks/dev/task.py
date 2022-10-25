import os
from typing import List, Optional, Union

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.task.context import TaskContext
from pctasks.task.task import Task


class TestTaskError(Exception):
    pass


class TestTaskOptions(PCBaseModel):
    num_outputs: int = 1
    fail_with: Optional[str] = None


class TestTaskInput(PCBaseModel):
    uri: Optional[str] = None
    check_exists_uri: Optional[str] = None
    output_dir: str
    options = TestTaskOptions()


class TestTaskOutput(PCBaseModel):
    uri: str
    uris: List[str]


class TaskRunHistory(PCBaseModel):
    input: TestTaskInput
    output_index: int


class TestTaskAsset(PCBaseModel):
    history: List[TaskRunHistory]


class TestTask(Task[TestTaskInput, TestTaskOutput]):
    _input_model = TestTaskInput
    _output_model = TestTaskOutput

    def run(
        self, input: TestTaskInput, context: TaskContext
    ) -> Union[TestTaskOutput, WaitTaskResult, FailedTaskResult]:
        history: List[TaskRunHistory] = []
        if input.uri:
            output_base_name = os.path.basename(input.uri)
            input_storage, input_path = context.storage_factory.get_storage_for_file(
                input.uri
            )

            if not input_storage.file_exists(input_path):
                raise TestTaskError(f"Input file {input.uri} does not exist.")

            try:
                history = TestTaskAsset.parse_obj(
                    input_storage.read_json(input_path)
                ).history
            except:
                # Assuming file is not a TestTaskAsset
                pass
        else:
            output_base_name = "test-output"

        if input.check_exists_uri:
            (
                check_exists_storage,
                check_exists_path,
            ) = context.storage_factory.get_storage_for_file(input.check_exists_uri)
            if not check_exists_storage.file_exists(check_exists_path):
                raise Exception(
                    f"Check exists file {input.check_exists_uri} does not exist."
                )

        outputs: List[str] = []
        output_storage = context.storage_factory.get_storage(input.output_dir)
        for i in range(0, max(input.options.num_outputs, 1)):
            output_path = f"{output_base_name}-{i}"
            output_storage.write_dict(
                output_path,
                TestTaskAsset(
                    history=history + [TaskRunHistory(input=input, output_index=i)]
                ).dict(),
            )
            outputs.append(output_storage.get_uri(output_path))

        return TestTaskOutput(uri=outputs[0], uris=outputs)


test_task = TestTask()
