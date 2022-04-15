from datetime import datetime
import os
from typing import List, Optional
from pctasks.core.models.base import PCBaseModel
from pctasks.task.context import TaskContext
from pctasks.task.task import Task
from pctasks.task.utils import get_task_path


class ListFilesInput(PCBaseModel):
    src_uri: str
    """The URI of the source directory to list files from."""

    name_starts_with: Optional[str] = None
    """Only include files that start with this string."""

    since: Optional[datetime] = None
    """Only include files that have been modified since this time."""

    extensions: Optional[List[str]] = None
    """Only include files with an extension in this list."""

    ends_with: Optional[str] = None
    """Only include files that end with this string."""

    matches: Optional[str] = None
    """Only include files that match this regex."""

    limit: Optional[int] = None
    """Limit the number of files to return. """


class ListFilesOutput(PCBaseModel):
    uris: List[str]


class ListFilesTask(Task[ListFilesInput, ListFilesOutput]):
    _input_model = ListFilesInput
    _output_model = ListFilesOutput

    def run(self, input: ListFilesInput, context: TaskContext) -> ListFilesOutput:
        storage = context.storage_factory.get_storage(input.src_uri)
        result = []
        for root, _, files in storage.walk(
            name_starts_with=input.name_starts_with,
            since_date=input.since,
            extensions=input.extensions,
            ends_with=input.ends_with,
            matches=input.matches,
            file_limit=input.limit,
        ):
            result.extend(
                [storage.get_uri(os.path.join(root, f).strip("./")) for f in files]
            )
        return ListFilesOutput(uris=result)


task = ListFilesTask()
TASK_PATH = get_task_path(task, "task")
