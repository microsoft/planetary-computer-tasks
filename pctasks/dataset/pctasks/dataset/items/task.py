import logging
import os
from typing import Callable, List, Union

import orjson
import pystac

from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.chunks.chunkset import ChunkSet
from pctasks.dataset.items.models import CreateItemsInput, CreateItemsOutput
from pctasks.task import Task
from pctasks.task.context import TaskContext

logger = logging.getLogger(__name__)


class CreateItemsError(Exception):
    pass


CreateItemFunc = Callable[
    [str, StorageFactory], Union[List[pystac.Item], WaitTaskResult]
]


class OutputNDJSONRequired(Exception):
    pass


def asset_chunk_id_to_ndjson_chunk_id(asset_chunk_id: str) -> str:
    folder_name = os.path.dirname(asset_chunk_id)
    return os.path.join(folder_name, "items.ndjson")


class CreateItemsTask(Task[CreateItemsInput, CreateItemsOutput]):
    _input_model = CreateItemsInput
    _output_model = CreateItemsOutput

    def __init__(
        self,
        create_item: CreateItemFunc,
    ) -> None:
        super().__init__()
        self._create_item = create_item

    def create_items(
        self, args: CreateItemsInput, context: TaskContext
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        storage_factory = context.storage_factory
        results: List[pystac.Item] = []

        def _validate(items: List[pystac.Item]) -> None:
            if not args.options.skip_validation:
                for item in items:
                    item.validate()

        if args.asset_uri:
            try:
                result = self._create_item(args.asset_uri, storage_factory)
            except Exception as e:
                raise CreateItemsError(
                    f"Failed to create item from {args.asset_uri}"
                ) from e
            if isinstance(result, WaitTaskResult):
                return result
            else:
                _validate(result)
                results.extend(result)
        elif args.asset_chunk_info:
            chunk_storage, chunk_path = storage_factory.get_storage_for_file(
                args.asset_chunk_info.uri
            )
            chunk_lines = chunk_storage.read_text(chunk_path).splitlines()
            if args.options.limit:
                chunk_lines = chunk_lines[: args.options.limit]
            for asset_uri in chunk_lines:
                try:
                    result = self._create_item(asset_uri, storage_factory)
                except Exception as e:
                    raise CreateItemsError(
                        f"Failed to create item from {asset_uri}"
                    ) from e
                if isinstance(result, WaitTaskResult):
                    return result
                else:
                    _validate(result)
                    results.extend(result)

                if args.collection_id:
                    for item in results:
                        item.collection_id = args.collection_id

        else:
            # Should be prevented by validator
            raise ValueError("Neither asset_uri nor chunk_uri specified")

        return results

    def run(
        self, input: CreateItemsInput, context: TaskContext
    ) -> Union[CreateItemsOutput, WaitTaskResult, FailedTaskResult]:
        results = self.create_items(input, context)

        if isinstance(results, WaitTaskResult):
            return results
        elif isinstance(results, FailedTaskResult):
            return results
        else:
            output: CreateItemsOutput
            if len(results) == 1:
                output = CreateItemsOutput(item=results[0].to_dict())
            else:
                # Save ndjson

                if not input.item_chunkset_uri:
                    raise OutputNDJSONRequired("item_chunkset_uri must be specified")

                if not input.asset_chunk_info:
                    raise OutputNDJSONRequired("chunkset_id must be specified")

                storage = context.storage_factory.get_storage(input.item_chunkset_uri)
                chunkset = ChunkSet(storage)

                items_chunk_id = asset_chunk_id_to_ndjson_chunk_id(
                    input.asset_chunk_info.chunk_id
                )
                chunkset.write_chunk(
                    items_chunk_id,
                    [orjson.dumps(item.to_dict()) for item in results],
                )

                output = CreateItemsOutput(
                    ndjson_uri=chunkset.get_chunk_uri(items_chunk_id)
                )

            return output
