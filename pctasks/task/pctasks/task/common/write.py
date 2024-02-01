from typing import Any, Dict, List, Union

import orjson

from pctasks.core.models.base import PCBaseModel
from pctasks.task.context import TaskContext
from pctasks.task.task import Task
from pctasks.task.utils import get_task_path


class WriteInput(PCBaseModel):
    content: Union[str, List[Any], Dict[str, Any]]
    """Content to write"""

    uri: str
    """The URI to write to."""


class WriteOutput(PCBaseModel):
    uri: str
    """The URI that was written to"""


class WriteTask(Task[WriteInput, WriteOutput]):
    _input_model = WriteInput
    _output_model = WriteOutput

    def run(self, input: WriteInput, context: TaskContext) -> WriteOutput:
        storage, path = context.storage_factory.get_storage_for_file(input.uri)
        if isinstance(input.content, str):
            storage.write_text(path, input.content)
        else:
            storage.write_bytes(
                path, orjson.dumps(input.content, orjson.OPT_SERIALIZE_NUMPY)
            )

        return WriteOutput(uri=input.uri)


task = WriteTask()
TASK_PATH = get_task_path(task, "task")
