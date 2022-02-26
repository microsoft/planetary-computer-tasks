from pathlib import Path
from typing import List

from pctasks.core.models.base import PCBaseModel
from pctasks.task.context import TaskContext
from pctasks.task.task import Task


class ListPrefixesInput(PCBaseModel):
    uri: str
    depth: int


class ListprefixesOutput(PCBaseModel):
    uris: List[str]


class ListPrefixesTask(Task[ListPrefixesInput, ListprefixesOutput]):
    _input_model = ListPrefixesInput
    _output_model = ListprefixesOutput

    def run(self, input: ListPrefixesInput, context: TaskContext) -> ListprefixesOutput:
        storage = context.storage_factory.get_storage(input.uri)
        prefix_uris: List[str] = []
        for root, _, _ in storage.walk(min_depth=input.depth, max_depth=input.depth):
            prefix_uris.append(storage.get_uri(root))
        return ListprefixesOutput(uris=prefix_uris)


class ListFilesTaskInput(PCBaseModel):
    uri: str


class ListFilesTaskOutput(PCBaseModel):
    uris: List[str]


class ListFilesTask(Task[ListFilesTaskInput, ListFilesTaskOutput]):
    _input_model = ListFilesTaskInput
    _output_model = ListFilesTaskOutput

    def run(
        self, input: ListFilesTaskInput, context: TaskContext
    ) -> ListFilesTaskOutput:
        storage = context.storage_factory.get_storage(input.uri)
        return ListFilesTaskOutput(
            uris=[storage.get_uri(p) for p in storage.list_files()]
        )


class ReadFileTaskInput(PCBaseModel):
    uri: str


class ReadFileTaskOutput(PCBaseModel):
    content: str
    uri: str
    name: str


class ReadFileTask(Task[ReadFileTaskInput, ReadFileTaskOutput]):
    _input_model = ReadFileTaskInput
    _output_model = ReadFileTaskOutput

    def run(self, input: ReadFileTaskInput, context: TaskContext) -> ReadFileTaskOutput:
        storage, path = context.storage_factory.get_storage_for_file(input.uri)
        return ReadFileTaskOutput(
            content=storage.read_text(path),
            uri=input.uri,
            name=Path(input.uri).name,
        )


class WriteFileTaskInput(PCBaseModel):
    uri: str
    content: str


class WriteFileTaskOutput(PCBaseModel):
    uri: str


class WriteFileTask(Task[WriteFileTaskInput, WriteFileTaskOutput]):
    _input_model = WriteFileTaskInput
    _output_model = WriteFileTaskOutput

    def run(
        self, input: WriteFileTaskInput, context: TaskContext
    ) -> WriteFileTaskOutput:
        storage, path = context.storage_factory.get_storage_for_file(input.uri)
        storage.write_text(path, input.content)
        return WriteFileTaskOutput(uri=input.uri)


list_prefixes_task = ListPrefixesTask()
list_files_task = ListFilesTask()
read_file_task = ReadFileTask()
write_file_task = WriteFileTask()
