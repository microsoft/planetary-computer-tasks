import logging
import os
import time
from typing import Callable, List, Optional, Union

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


CreateItemFunc = Callable[
    [str, StorageFactory], Union[List[pystac.Item], WaitTaskResult]
]


class OutputNDJSONRequired(Exception):
    pass


def asset_chunk_id_to_ndjson_chunk_id(asset_chunk_id: str) -> str:
    folder_name = os.path.dirname(asset_chunk_id)
    return os.path.join(folder_name, "items.ndjson")


def validate_item(item: pystac.Item, collection_id: Optional[str]) -> pystac.Item:
    """
    Validate a pystac Item.

    This method will validate

    1. That the item is a valid STAC item (using its JSON Schema)
    2. Verify that the item has a ``collection_id`` is set or sets it to
       ``collection_id`` if that's provided. If it's set in both places,
       then they must match.

    Parameters
    ----------
    item: pystac.Item
    collection_id: str
        The ID of the STAC collection this item will be ingested to.

    Returns
    -------
    item: pystac.Item
        The validated STAC item.
    """
    if collection_id:
        if item.collection_id and item.collection_id != collection_id:
            raise CreateItemsError(
                f"Item {item.id} has collection {item.collection_id} "
                f"but expected {collection_id}"
            )
        else:
            item = item.clone()  # only copy if needed
            item.collection_id = collection_id
    else:
        if not item.collection_id:
            raise CreateItemsError(f"Item {item.id} has no collection ID set.")

    # Avoid validation error for missing collection link
    remove_collection_link = False

    if item.collection_id and not item.get_single_link("collection"):
        # TODO: avoid mutating `item`.
        # For valid items, users shouldn't ever see this link we add. But if
        # `item.validate()` throws an exception they'll get back an item with a
        # new link.
        item.add_link(pystac.Link(rel="collection", target="http://example.com"))
        remove_collection_link = True

    item.validate()

    if remove_collection_link:
        item.remove_links("collection")

    return item


def validate_create_items_result(
    items: List[pystac.Item],
    collection_id: Optional[str],
    skip_validation: bool = False,
) -> List[pystac.Item]:
    if not skip_validation:
        items = [validate_item(item, collection_id=collection_id) for item in items]
    return items


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
                raise CreateItemsError(
                    f"Failed to create item from {args.asset_uri}"
                ) from e
            if isinstance(result, WaitTaskResult):
                return result
            elif result is None:
                logger.warning(f"No items created from {args.asset_uri}")
            else:
                results = validate_create_items_result(
                    result,
                    collection_id=args.collection_id,
                    skip_validation=args.options.skip_validation,
                )
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
                except Exception as e:
                    raise CreateItemsError(
                        f"Failed to create item from {asset_uri}"
                    ) from e
                if isinstance(result, WaitTaskResult):
                    return result
                else:
                    if not result:
                        logger.warning(f"No items created from {asset_uri}")
                    else:
                        results = validate_create_items_result(
                            result,
                            collection_id=args.collection_id,
                            skip_validation=args.options.skip_validation,
                        )

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
