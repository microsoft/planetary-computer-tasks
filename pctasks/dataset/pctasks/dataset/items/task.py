import logging
import os
import textwrap
import time
import traceback
from typing import Callable, List, Tuple, Union

import orjson
import pystac

from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.chunks.chunkset import ChunkSet
from pctasks.dataset.items.models import CreateItemsInput, CreateItemsOutput
from pctasks.task.context import TaskContext
from pctasks.task.task import Task

logger = logging.getLogger(__name__)


class CreateItemsError(Exception):
    pass


class CreateItemsMultiError(Exception):
    def __init__(self, asset_uris: List[str], rendered_tracebacks: List[str]):
        self.asset_uris = asset_uris
        self.rendered_tracebacks = rendered_tracebacks

    def __repr__(self):
        n = len(self.asset_uris)
        if n:
            sample_asset_uri = self.asset_uris[0]
            sample_traceback = self.rendered_tracebacks[0]
        else:
            sample_asset_uri = sample_traceback = None

        return textwrap.dedent("""\
        {n} failures during item creation.
        
        Sample asset uri:

            {sample_asset_uri}

        Sample traceback:

            {sample_traceback}
        """).format(n=n, sample_asset_uri=sample_asset_uri, sample_traceback=sample_traceback)

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
        exceptions: List[Tuple[str, str]] = []
        raise_exceptions = False

        def _validate(items: List[pystac.Item]) -> None:
            if not args.options.skip_validation:
                for item in items:
                    # Avoid validation error for missing collection link
                    remove_collection_link = False
                    if item.collection_id and not item.get_single_link("collection"):
                        item.add_link(
                            pystac.Link(rel="collection", target="http://example.com")
                        )
                        remove_collection_link = True
                    item.validate()
                    if remove_collection_link:
                        item.remove_links("collection")

        def _ensure_collection(items: List[pystac.Item]) -> None:
            for item in items:
                if args.collection_id:
                    if item.collection_id and item.collection_id != args.collection_id:
                        raise CreateItemsError(
                            f"Item {item.id} has collection {item.collection_id} "
                            f"but expected {args.collection_id}"
                        )
                    else:
                        item.collection_id = args.collection_id
                else:
                    if not item.collection_id:
                        raise CreateItemsError(
                            f"Item {item.id} has no collection ID set."
                        )

        if args.asset_uri:
            try:
                start_time = time.monotonic()
                result = self._create_item(args.asset_uri, storage_factory)
                end_time = time.monotonic()
                logger.info(
                    f"Created items from {args.asset_uri} in "
                    f"{end_time - start_time:.2f}s"
                )
            except Exception as e:
                logger.exception("Failed to create item from %s", args.asset_uri)
                exceptions.append()
                raise CreateItemsError(
                    f"Failed to create item from {args.asset_uri}"
                ) from e
            if isinstance(result, WaitTaskResult):
                return result
            else:
                if not result:
                    logger.warning(f"No items created from {args.asset_uri}")
                else:
                    _validate(result)
                    _ensure_collection(result)
                    results.extend(result)
        elif args.asset_chunk_info:
            chunk_storage, chunk_path = storage_factory.get_storage_for_file(
                args.asset_chunk_info.uri
            )
            chunk_lines = chunk_storage.read_text(chunk_path).splitlines()
            asset_count = len(chunk_lines)
            if args.options.limit:
                chunk_lines = chunk_lines[: args.options.limit]
            for i, asset_uri in enumerate(chunk_lines):
                try:
                    start_time = time.monotonic()
                    result = self._create_item(asset_uri, storage_factory)
                    end_time = time.monotonic()
                    logger.info(
                        f"({((i+1)/asset_count)*100:06.2f}%) "
                        f"[{end_time - start_time:.2f}s] "
                        f" - {asset_uri} "
                        f"({i+1} of {asset_count})"
                    )
                except Exception:
                    logger.exception("Failed to create items from %s", asset_uri)
                    exceptions.append((asset_uri, traceback.format_exc()))
                    # We'll continue on processing items here. We'll re-raise the
                    # failures at the end.
                    continue
                if isinstance(result, WaitTaskResult):
                    return result
                else:
                    if not result:
                        logger.warning(f"No items created from {asset_uri}")
                    else:
                        _validate(result)
                        _ensure_collection(result)
                        results.extend(result)
            if exceptions and raise_exceptions:
                asset_uris, rendered_tracebacks = zip(*exceptions)
                raise CreateItemsMultiError(asset_uris, rendered_tracebacks)

        else:
            # Should be prevented by validator
            raise ValueError("Neither asset_uri nor chunk_uri specified")

        if args.collection_id:
            for item in results:
                item.collection_id = args.collection_id

        return results

    def run(
        self, input: CreateItemsInput, context: TaskContext
    ) -> Union[CreateItemsOutput, WaitTaskResult, FailedTaskResult]:
        logger.info("Creating items...")
        results = self.create_items(input, context)

        if isinstance(results, WaitTaskResult):
            return results
        elif isinstance(results, FailedTaskResult):
            return results
        else:
            output: CreateItemsOutput
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
