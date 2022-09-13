from typing import List

from pctasks.core.models.base import PCBaseModel
from pctasks.task.context import TaskContext
from pctasks.task.task import Task
from pctasks.task.utils import get_task_path


class ListPrefixesInput(PCBaseModel):
    src_uri: str
    """The URI of the source directory to list prefixes from."""

    depth: int
    """The depth of the prefixes to list."""


class ListPrefixesOutput(PCBaseModel):
    uris: List[str]


class ListPrefixesTask(Task[ListPrefixesInput, ListPrefixesOutput]):
    """List prefixes in storage.

    This can be used to parallelize downstream tasks based on
    a partitioning of storage directories.
    """

    _input_model = ListPrefixesInput
    _output_model = ListPrefixesOutput

    def run(self, input: ListPrefixesInput, context: TaskContext) -> ListPrefixesOutput:
        storage = context.storage_factory.get_storage(input.src_uri)
        result = [
            storage.get_uri(root)
            for root, _, _ in storage.walk(max_depth=input.depth, min_depth=input.depth)
        ]
        return ListPrefixesOutput(uris=result)


task = ListPrefixesTask()
TASK_PATH = get_task_path(task, "task")
