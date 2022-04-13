import logging
import os
from tempfile import TemporaryDirectory
from typing import List, Union
from urllib.parse import urlparse

from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.core.utils import grouped
from pctasks.dataset.chunks.models import (
    ChunkInfo,
    CreateChunksInput,
    CreateChunksOutput,
)
from pctasks.task import Task
from pctasks.task.context import TaskContext

logger = logging.getLogger(__name__)


def uri_to_chunk_id(uri: str, num: int) -> str:
    parsed = urlparse(uri)
    if parsed.netloc:
        result = f"{parsed.netloc}{parsed.path}"
    else:
        result = parsed.path
    return f"{result.strip('/')}/{num}"


class CreateChunksTask(Task[CreateChunksInput, CreateChunksOutput]):
    _input_model = CreateChunksInput
    _output_model = CreateChunksOutput

    @classmethod
    def create_chunks(cls, input: CreateChunksInput) -> CreateChunksOutput:
        # Ensure options have been templated.
        if isinstance(input.options, str):
            raise ValueError(
                f"Options are string, did templating fail?: {input.options}"
            )

        src_storage = input.get_src_storage()
        dst_storage = input.get_dst_storage()

        asset_uris: List[str] = []
        for root, _, files in src_storage.walk(
            name_starts_with=input.options.name_starts_with,
            since_date=input.options.since,
            extensions=input.options.extensions,
            ends_with=input.options.ends_with,
            matches=input.options.matches,
            file_limit=input.options.limit,
        ):
            for f in files:
                asset_path = os.path.join(root, f).strip("./")
                asset_uris.append(src_storage.get_uri(asset_path))

        chunks: List[ChunkInfo] = []

        for i, chunk_lines in enumerate(
            grouped(asset_uris, input.options.get_chunk_length())
        ):
            chunk_id = uri_to_chunk_id(input.src_storage_uri, i)
            logger.info(f" -- Processing chunk {chunk_id}...")
            txt = "\n".join(chunk_lines)
            with TemporaryDirectory() as tmp_dir:
                tmp_path = os.path.join(tmp_dir, "list.csv")
                with open(tmp_path, "w") as f:
                    f.write(txt)
                dst_blob = (
                    f"{chunk_id}/{input.options.chunk_file_name}"
                    f"{input.options.chunk_extension}"
                )
                logger.info(f"Writing {dst_blob}...")
                dst_storage.upload_file(tmp_path, dst_blob)
                chunks.append(
                    ChunkInfo(uri=dst_storage.get_uri(dst_blob), chunk_id=chunk_id)
                )

        return CreateChunksOutput(chunks=chunks)

    def run(
        self, input: CreateChunksInput, context: TaskContext
    ) -> Union[CreateChunksOutput, WaitTaskResult, FailedTaskResult]:
        return self.create_chunks(input)


create_chunks_task = CreateChunksTask()
