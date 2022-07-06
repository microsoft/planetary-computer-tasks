import logging
import os
from typing import List, Union
from urllib.parse import urlparse

from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.utils import grouped
from pctasks.dataset.chunks.chunkset import ChunkSet
from pctasks.dataset.chunks.models import (
    ChunkInfo,
    ChunksOutput,
    CreateChunksInput,
    ListChunksInput,
)
from pctasks.task.task import Task
from pctasks.task.context import TaskContext

logger = logging.getLogger(__name__)


def uri_to_chunk_id(uri: str, num: int, file_name: str, extension: str) -> str:
    parsed = urlparse(uri)
    if parsed.netloc:
        result = f"{parsed.netloc}{parsed.path}"
    else:
        result = parsed.path
    return f"{result.strip('/')}/{num}/{file_name}{extension}"


class CreateChunksTask(Task[CreateChunksInput, ChunksOutput]):
    _input_model = CreateChunksInput
    _output_model = ChunksOutput

    @classmethod
    def create_chunks(
        cls, input: CreateChunksInput, storage_factory: StorageFactory
    ) -> ChunksOutput:
        # Ensure options have been templated.
        if isinstance(input.options, str):
            raise ValueError(
                f"Options are string, did templating fail?: {input.options}"
            )

        src_storage = storage_factory.get_storage(input.src_uri)
        dst_storage = storage_factory.get_storage(input.dst_uri)

        chunkset = ChunkSet(dst_storage)

        asset_uris: List[str] = []
        for root, folders, files in src_storage.walk(
            name_starts_with=input.options.name_starts_with,
            since_date=input.options.since,
            extensions=input.options.extensions,
            ends_with=input.options.ends_with,
            matches=input.options.matches,
            file_limit=input.options.limit,
            max_depth=input.options.max_depth,
        ):
            if input.options.list_folders:
                gen = folders
            else:
                gen = files
            for f in gen:
                asset_path = os.path.join(root, f).strip("./")
                asset_uris.append(src_storage.get_uri(asset_path))

        chunks: List[ChunkInfo] = []

        for i, chunk_lines in enumerate(
            grouped(asset_uris, input.options.get_chunk_length())
        ):
            chunk_id = uri_to_chunk_id(
                input.src_uri,
                i,
                input.options.chunk_file_name,
                input.options.chunk_extension,
            )
            logger.info(f" -- Processing chunk {chunk_id}...")
            chunkset.write_chunk(chunk_id, list(chunk_lines))
            chunks.append(
                ChunkInfo(uri=chunkset.get_chunk_uri(chunk_id), chunk_id=chunk_id)
            )

        return ChunksOutput(chunks=chunks)

    def run(
        self, input: CreateChunksInput, context: TaskContext
    ) -> Union[ChunksOutput, WaitTaskResult, FailedTaskResult]:
        return self.create_chunks(input, context.storage_factory)


create_chunks_task = CreateChunksTask()


class ListChunksTask(Task[ListChunksInput, ChunksOutput]):
    _input_model = ListChunksInput
    _output_model = ChunksOutput

    @classmethod
    def create_chunks(
        cls, input: ListChunksInput, storage_factory: StorageFactory
    ) -> ChunksOutput:
        chunk_storage = storage_factory.get_storage(input.chunkset_uri)

        chunkset = ChunkSet(chunk_storage)

        if input.all:
            chunk_ids = chunkset.all_chunks
        else:
            chunk_ids = chunkset.unprocessed_chunks

        chunks: List[ChunkInfo] = [
            ChunkInfo(uri=chunkset.get_chunk_uri(chunk_id), chunk_id=chunk_id)
            for chunk_id in chunk_ids
        ]

        return ChunksOutput(chunks=chunks)

    def run(
        self, input: ListChunksInput, context: TaskContext
    ) -> Union[ChunksOutput, WaitTaskResult, FailedTaskResult]:
        return self.create_chunks(input, context.storage_factory)


list_chunks_task = ListChunksTask()
