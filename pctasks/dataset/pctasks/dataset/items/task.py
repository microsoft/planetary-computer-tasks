import contextlib
import functools
import logging
import os
import signal
import time
from typing import Any, Callable, Iterator, List, Optional, Union

import orjson
import pystac
from opencensus.ext.azure.log_exporter import AzureLogHandler

from pctasks.core.models.task import FailedTaskResult, WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.dataset.chunks.chunkset import ChunkSet
from pctasks.dataset.items.models import CreateItemsInput, CreateItemsOutput
from pctasks.task.context import TaskContext
from pctasks.task.task import Task

logger = logging.getLogger(__name__)
azlogger = logging.getLogger("monitor.pctasks.dataset.items.task")
azlogger.setLevel(logging.INFO)
azhandler = None  # initialized later in `_init_azlogger`


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


def _init_azlogger() -> None:
    # AzureLogHandler is slow to initialize
    # do it once here
    global azhandler

    if azhandler is None:
        logger.debug("Initializing AzureLogHandler")
        try:
            azhandler = AzureLogHandler()
        except ValueError:
            # missing instrumentation key
            azhandler = False
            logger.warning("Unable to initialize AzureLogHandler")
        else:
            azhandler.setLevel(logging.INFO)
            azlogger.addHandler(azhandler)


class CreateItemsTimeoutError(TimeoutError):
    ...


def create_item_with_timeout(
    create_items_func: CreateItemFunc, timeout: Optional[int] = None
) -> CreateItemFunc:
    """
     A wrapper for `create_items_func` to enforce a timeout.

     Parameters
     ----------
     create_items_func: callable
         The create items function to run under the timeout
     timeout: int, optional
         The timeout in seconds.

     Notes
    -----
     When `timeout` is specified, this registers a signal handler for
     ``signal.SIGALRM``. Your ``create_items_func`` must finished within
     ``timeout`` seconds. If it's not finished, the call is forcibly
     interrupted. We'll try the function up to 3 times before raising
     a :class:`CreateItemsTimeoutError`.
    """
    if timeout is None:
        return create_items_func

    # Do this once
    def handler(signal_received: Any, frame: Any) -> Any:
        raise CreateItemsTimeoutError(
            f"Timed out during create items after {timeout} seconds"
        )

    signal.signal(signal.SIGALRM, handler)

    @functools.wraps(create_items_func)
    def inner(*args: Any, **kwargs: Any) -> Union[List[pystac.Item], WaitTaskResult]:
        assert timeout is not None
        for i in range(3):
            try:
                signal.alarm(timeout)
                result = create_items_func(*args, **kwargs)
                signal.alarm(0)  # clear the signal
            except CreateItemsTimeoutError as e:
                logger.warning(f"Timeout during create items (attempt {i + 1}/3)")
                err = e
            else:
                return result
        else:
            raise err

    return inner


@contextlib.contextmanager
def traced_create_item(
    asset_uri: str,
    collection_id: Optional[str],
    i: Optional[int] = None,
    asset_count: Optional[int] = None,
) -> Iterator[None]:
    _init_azlogger()
    start_time = time.monotonic()
    yield
    end_time = time.monotonic()

    if i is not None and asset_count is not None:
        # asset_chunk_info case
        logger.info(
            f"({((i+1)/asset_count)*100:06.2f}%) "
            f"[{end_time - start_time:.2f}s] "
            f" - {asset_uri} "
            f"({i+1} of {asset_count})"
        )
    else:
        # asset_uri case
        logger.info(
            f"Created items from {asset_uri} in " f"{end_time - start_time:.2f}s"
        )

    properties = {
        "custom_dimensions": {
            "type": "pctasks.create_item",
            "collection_id": collection_id,
            "asset_uri": asset_uri,
            "duration_seconds": end_time - start_time,
        }
    }
    azlogger.info("Created item", extra=properties)


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

        if args.options.timeout is not None:
            create_item_func = create_item_with_timeout(
                self._create_item, timeout=args.options.timeout
            )
        else:
            create_item_func = self._create_item

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
                with traced_create_item(args.asset_uri, args.collection_id):
                    result = create_item_func(args.asset_uri, storage_factory)
            except Exception as e:
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
                    with traced_create_item(
                        asset_uri, args.collection_id, i=i, asset_count=asset_count
                    ):
                        result = create_item_func(asset_uri, storage_factory)
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
                        _validate(result)
                        _ensure_collection(result)
                        results.extend(result)

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
