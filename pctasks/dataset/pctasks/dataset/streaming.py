from __future__ import annotations

import dataclasses
import datetime
import importlib.metadata
import json
import logging
import urllib.parse
import uuid
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

import azure.core.credentials
import azure.cosmos
import azure.identity
import azure.storage.queue
import pystac

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import TaskDefinition, WaitTaskResult
from pctasks.core.storage import StorageFactory

# # TODO: check import / dependency order
# from pctasks.dataset.items.task import (
#     validate_item,
# )
from pctasks.task.context import TaskContext
from pctasks.task.streaming import NoOutput, StreamingTaskOptions, StreamingTaskMixin
from pctasks.task.task import Task

logger = logging.getLogger("pctasks.dataset.streaming")


def event_id_factory() -> str:
    return str(uuid.uuid4())


def time_factory() -> str:
    # TODO: can this be a datetime in python?
    return datetime.datetime.utcnow().isoformat() + "Z"


def transform_url(event_url: str) -> str:
    # Why is this needed?
    # To transform from EventGrid / Blob style HTTP urls to
    # pctask's blob:// style urls.
    if event_url.startswith("http"):
        parsed = urllib.parse.urlparse(event_url)
        account_name = parsed.netloc.split(".")[0]
        return f"blob://{account_name}{parsed.path}"
    return event_url


@dataclasses.dataclass
class ItemCreatedMetrics:
    storage_event_time: str
    message_inserted_time: str


@dataclasses.dataclass
class ItemCreatedData:
    item: dict[str, Any]
    metrics: ItemCreatedMetrics


@dataclasses.dataclass
class ItemCreatedEvent:
    data: ItemCreatedData
    specversion: str = "1.0"
    type: str = "com.microsoft.planetarycomputer/item-created"
    source: str = "pctasks"
    id: str = dataclasses.field(default_factory=event_id_factory)
    time: str = dataclasses.field(default_factory=time_factory)
    datacontenttype: str = "application/json"


class StreamingCreateItemsOptions(PCBaseModel):
    """
    Create items from a stream of messages.
    """
    skip_validation: bool = False
    """Skip validation through PySTAC of the STAC Items."""


class StreamingCreateItemsInput(PCBaseModel):
    """
    Input for a streaming create items task.

    Parameters
    ----------
    queue_url: str
        The full URL to the queue this task is processing. This will typically
        be like ``https://<account-name>.queue.core.windows.net/<queue-name>``
    visibility_timeout: int
        The number of seconds to before the queue service assumes processing
        fails and makes the message visible again. This should be some multiple
        of the typical processing time.
    min_replica_count, max_replica_count: int
        The minimum and maximum number of concurrent workers that should process
        items from this queue.
    polling_interval: int, default 30
        How often KEDA should poll the queue to check for new messages and
        rescale.
    trigger_queue_length: int, default 100
        Controls the scaling factor.
    message_limit: Optional[int]
        The maximum number of messages from the queue to process. Once reached,
        the processing function will exit. If not set, the function will run
        forever, relying on some external system (like KEDA) to stop processing.

        This is primarily useful for testing.

    collection_id: str
        The STAC collection ID for items in this queue.
    options: StreamingCreateItemsOptions
        Additional options...
    cosmos_endpoint: str
        The full endpoint to the Cosmos DB account where STAC items will be
        written to. This will be like
        ``https://<account-name>.documents.azure.com:443/``.
    cosmos_credential: str, optional
        An account key for Cosmos DB. By default, ``DefaultAzureCredential`` is
        used.
    db_name: str
        The Cosmos DB database name the STAC items are written to.
    container_name: str
        The Cosmos DB container name the STAC items are written to.
    create_items_function: str or callable.
        A callable or entrypoints-style path to a callable that creates the STAC
        item.
    """
    streaming_options: StreamingTaskOptions
    collection_id: str
    options: StreamingCreateItemsOptions = StreamingCreateItemsOptions()
    cosmos_endpoint: str = (
        "https://pclowlatencytesttom.documents.azure.com:443/"  # TODO: config?
    )
    cosmos_credential: Optional[str] = None
    db_name: str = "lowlatencydb"  # TODO: config?
    container_name: str = "items"  # TODO: config?
    create_items_function: Union[
        str, Callable[[str, StorageFactory], List[pystac.Item]]
    ]  # can't use callable & entrypoint string

    class Config:
        extra = "forbid"

# TODO: Create a base streaming task
# - Inherited Ingest streaming task, in pctasks.ingest_task
# - Inherited CreateItems streaming task, in pctasks.dataset


class StreamingCreateItemsTask(
    StreamingTaskMixin, Task[StreamingCreateItemsInput, NoOutput]
):
    _input_model = StreamingCreateItemsInput
    _output_model = NoOutput

    # mypy doesn't like that `input` is a subclass of the type required
    # by the parent.
    def get_extra_options(  # type: ignore
        self, input: StreamingCreateItemsInput, context: TaskContext
    ) -> Dict[str, Any]:
        # TODO: Used DefaultAzureCredential in dev / test too.
        credential: Union[str, azure.core.credentials.TokenCredential]
        if input.cosmos_credential:
            credential = input.cosmos_credential
        else:
            credential = azure.identity.DefaultAzureCredential()
        container_proxy = (
            azure.cosmos.CosmosClient(input.cosmos_endpoint, credential)
            .get_database_client(input.db_name)
            .get_container_client(input.container_name)
        )
        create_items_function = input.create_items_function
        if isinstance(create_items_function, str):
            logger.info("Loading create_items_function")
            entrypoint = importlib.metadata.EntryPoint("", create_items_function, "")
            create_items_function = entrypoint.load()
        assert callable(create_items_function)

        return {
            "container_proxy": container_proxy,
            "create_items_function": create_items_function,
        }

    def create_items(
        self,
        message_data: dict[str, Any],
        create_items_function: Callable[[str, StorageFactory], List[pystac.Item]],
        storage_factory: StorageFactory,
        collection_id: str,
        skip_validation: bool = False,
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        # url = transform_url(message_data["url"])
        url = message_data["url"]
        items = create_items_function(url, storage_factory)

        if collection_id:
            for item in items:
                item.collection_id = collection_id

        # TODO: refactor item validation
        # if not skip_validation:
        #     for item in items:
        #         validate_item(item)
        return items

    # mypy doesn't like the child bringing in extra arguments, which is fair.
    # We can't get these off `input` though, unless it were
    # to cache the stuff.
    def process_message(  # type: ignore
        self,
        message: azure.storage.queue.QueueMessage,
        input: StreamingCreateItemsInput,
        context: TaskContext,
        container_proxy: azure.cosmos.ContainerProxy,
        create_items_function: Callable[[str, StorageFactory], List[pystac.Item]],
    ) -> None:
        logger.info("Processing message id=%s", message.id)
        parsed_message = json.loads(message.content)
        if not callable(input.create_items_function):
            # Why isn't this already done?
            logger.info("Loading create_items_functio")
            entrypoint = importlib.metadata.EntryPoint(
                "", input.create_items_function, ""
            )
            input.create_items_function = entrypoint.load()
        assert callable(
            input.create_items_function
        )  # convince mypy that this is the function.
        create_items_function = input.create_items_function

        try:
            items = self.create_items(
                parsed_message["data"],
                create_items_function=create_items_function,
                storage_factory=context.storage_factory,
                collection_id=input.collection_id,
            )
            # TODO: item validation, collection handling, etc.
        except Exception:
            # what to do here?
            # We probably want to shove these to some other "errors" container
            logger.exception("Error in create item")
            raise
        else:
            for item in items:
                # TODO: Proper error handling here.
                if isinstance(item, pystac.Item):
                    logger.info("Created item id=%s", item.id)
                    data = ItemCreatedData(
                        item=item.to_dict(),
                        metrics=ItemCreatedMetrics(
                            storage_event_time=parsed_message["time"],
                            message_inserted_time=message.inserted_on.strftime(
                                "%Y-%m-%dT%H:%M:%S.%fZ"
                            ),
                        ),
                    )
                    event = dataclasses.asdict(ItemCreatedEvent(data=data))
                    container_proxy.upsert_item(event)
                    logger.info("Persisted event id=%s", event["id"])


def create_item_from_item_uri(
    asset_uri: str, storage_factory: StorageFactory
) -> Union[List[pystac.Item], WaitTaskResult]:
    """
    Create a STAC item by reading the file.

    Parameters
    ----------
    asset_uri : str
        The pctasks-style URI to a JSON file containing
        a single STAC item.
    storage_factory : StorageFactory

    Examples
    --------
    >>> create_item_from_item_uri(
    ...     "blob://sentinel1euwestrtc/sentinel1-grd-rtc-stac/GRD/2023/2/28/IW/DH/S1A_IW_GRDH_1SDH_20230228T091754_20230228T091816_047434_05B1CE_rtc.json",  # noqa: E501
    ...     StorageFactory()
    ... )
    [<Item id=S1A_IW_GRDH_1SDH_20230228T091754_20230228T091816_047434_05B1CE_rtc>]
    """
    storage, path = storage_factory.get_storage_for_file(asset_uri)
    logger.debug("Reading file. asset_uri=%s path=%s", asset_uri, path)

    data = storage.read_json(path)
    item = pystac.Item.from_dict(data)

    return [item]


def create_item_from_message(asset_uri, storage_factory):
    # Just shoving the STAC item in the "url" field of the message.
    # data = json.loads(asset_uri)
    return [pystac.Item.from_dict(asset_uri)]
