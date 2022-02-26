import logging
import os
import re
from itertools import islice
from tempfile import TemporaryDirectory
from typing import List, Optional, Set, Union

from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.core.utils import grouped
from pctasks.dataset.chunks.models import CreateChunksInput, CreateChunksOutput
from pctasks.task import Task
from pctasks.task.context import TaskContext

logger = logging.getLogger(__name__)


class CreateChunksTask(Task[CreateChunksInput, CreateChunksOutput]):
    _input_model = CreateChunksInput
    _output_model = CreateChunksOutput

    @classmethod
    def create_chunks(cls, input: CreateChunksInput) -> CreateChunksOutput:
        src_storage = input.get_src_storage()
        dst_storage = input.get_dst_storage()

        files = src_storage.list_files(
            name_starts_with=input.name_starts_with, since_date=input.since
        )
        compiled_regex: Optional[re.Pattern]
        if input.matches is not None:
            compiled_regex = re.compile(input.matches)
        else:
            compiled_regex = None

        extensions: Optional[Set[str]] = None
        if input.extensions:
            extensions = set()
            for ext in input.extensions:
                if not ext.startswith("."):
                    ext = f".{ext}"
                extensions.add(ext.lower())

        def file_filter(blob: str) -> bool:
            ext = os.path.splitext(blob)[1]
            result = ext != ""
            if extensions:
                result &= ext in extensions
            if input.ends_with is not None:
                result &= blob.endswith(input.ends_with)
            if compiled_regex is not None:
                result &= compiled_regex.search(blob) is not None
            if result:
                logger.debug(f" ~ Found {blob}")
            return result

        files = filter(file_filter, files)
        files = map(lambda path: src_storage.get_uri(path), files)

        if input.limit is not None:
            files = islice(files, input.limit)

        chunk_uris: List[str] = []

        for i, chunk in enumerate(grouped(files, input.chunk_length)):
            logger.info(f" -- Processing chunk {i}...")
            txt = "\n".join(chunk)
            with TemporaryDirectory() as tmp_dir:
                tmp_path = os.path.join(tmp_dir, "list.csv")
                with open(tmp_path, "w") as f:
                    f.write(txt)
                dst_blob = f"{input.chunk_prefix}{i}{input.chunk_extension}"
                logger.info(f"Writing {dst_blob}...")
                dst_storage.upload_file(tmp_path, dst_blob)
                chunk_uris.append(dst_storage.get_uri(dst_blob))

        return CreateChunksOutput(chunk_uris=chunk_uris)

    def run(
        self, input: CreateChunksInput, context: TaskContext
    ) -> Union[CreateChunksOutput, WaitTaskResult, FailedTaskResult]:
        return self.create_chunks(input)


create_chunks_task = CreateChunksTask()
