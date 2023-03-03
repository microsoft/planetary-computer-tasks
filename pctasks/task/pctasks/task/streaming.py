from __future__ import annotations

import dataclasses
import datetime
import importlib.metadata
import json
import logging
import time
import urllib.parse
import uuid
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

import azure.cosmos
import azure.identity
import azure.storage.queue
import pystac

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import TaskDefinition, WaitTaskResult
from pctasks.core.storage import StorageFactory

if TYPE_CHECKING:
    from pctasks.ingest_task.pgstac import PgSTAC

# # TODO: check import / dependency order
# from pctasks.dataset.items.task import (
#     validate_item,
# )
from pctasks.task.context import TaskContext
from pctasks.task.task import Task

logger = logging.getLogger("pctasks.task.streaming")


def event_id_factory() -> str:
    return str(uuid.uuid4())


def time_factory() -> str:
    # TODO: can this be a datetime in python?
    return datetime.datetime.utcnow().isoformat() + "Z"


def transform_url(event_url: str) -> str:
    parsed = urllib.parse.urlparse(event_url)
    account_name = parsed.netloc.split(".")[0]
    return f"blob://{account_name}{parsed.path}"


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

    # TODO: limit?

    skip_validation: bool = False
    """Skip validation through PySTAC of the STAC Items."""


class StreamingCreateItemsInput(PCBaseModel):
    """
    Create items from a stream of messages.

    Parameters
    ----------
    queue_url: str
        The full URL to the queue this task is processing. This will typically
        be like ``https://<account-name>.queue.core.windows.net/<queue-name>``
    visibility_timeout: int
        The number of seconds to before the queue service assumes processing
        fails and makes the message visible again. This should be some multiple
        of the typical processing time.
    options: StreamingCreateItemsOptions
        Additional options...
    cosmos_endpoint: str
        The full endpoint to the Cosmos DB account where STAC items will be
        written to. This will be like
        ``https://<account-name>.documents.azure.com:443/``.
    db_name: str
        The Cosmos DB database name the STAC items are written to.
    container_name: str
        The Cosmos DB container name the STAC items are written to.
    create_items_function: str
        The entrypoints-style path to a callable that creates the STAC item.
    min_replica_count, max_replica_count: int
        The minimum and maximum number of concurrent workers that should process
        items from this queue.
    polling_interval: int, default 30
        How often KEDA should poll the queue to check for new messages and rescale.
    trigger_queue_length: int, default 100
        Controls the scaling factor.
    collection_id: str
        The STAC collection ID for items in this queue.
    """

    queue_url: str
    visibility_timeout: int
    collection_id: str
    options: StreamingCreateItemsOptions = StreamingCreateItemsOptions()
    cosmos_endpoint: str = (
        "https://pclowlatencytesttom.documents.azure.com:443/"  # TODO: config?
    )
    db_name: str = "lowlatencydb"  # TODO: config?
    container_name: str = "items"  # TODO: config?
    create_items_function: str  # can't use callable & entrypoint string
    min_replica_count: int = 0
    max_replica_count: int = 100
    polling_interval: int = 30
    trigger_queue_length: int = 100  # should this not have a default?


class StreamingCreateItemsConfig(TaskDefinition):
    @classmethod
    def create(
        cls,
        task_id: str,
        visibility_timeout: int,
        queue_url: str,
        create_items_function: Callable[[str], List[pystac.Item]],
        collection_id: str,
        options: StreamingCreateItemsOptions = StreamingCreateItemsOptions(),
        cosmos_endpoint: str = "https://pclowlatencytesttom.documents.azure.com:443/",
        db_name: str = "lowlatencydb",
        container_name: str = "items",
        min_replica_count: int = 0,
        max_replica_count: int = 100,
        polling_interval: int = 30,
        trigger_queue_length: int = 100,
        image: Optional[str] = None,
        image_key: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        environment: Optional[Dict[str, str]] = None,
    ) -> TaskDefinition:
        data = StreamingCreateItemsInput(
            queue_url=queue_url,
            visibility_timeout=visibility_timeout,
            collection_id=collection_id,
            options=options,
            cosmos_endpoint=cosmos_endpoint,
            db_name=db_name,
            container_name=container_name,
            create_items_function=create_items_function,
            min_replica_count=min_replica_count,
            max_replica_count=max_replica_count,
            polling_interval=polling_interval,
            trigger_queue_length=trigger_queue_length,
        ).dict()
        return TaskDefinition(
            id=task_id,
            image=image,
            image_key=image_key,
            task="pctasks.task.streaming:StreamingCreateItemsTask",
            tags=tags,
            environment=environment,
            args=data,
        )


class NoOutput(PCBaseModel):
    # just for the type checker
    pass


# TODO: Create a base streaming task
# - Inherited Ingest streaming task, in pctasks.ingest_task
# - Inherited CreateItems streaming task, in pctasks.dataset

# Is this a task or a definition?
class StreamingCreateItemsTask(Task[StreamingCreateItemsInput, NoOutput]):
    _input_model = StreamingCreateItemsInput
    _output_model = NoOutput

    def create_items(
        self,
        message_data: dict[str, Any],
        create_items_function: Callable[[str, StorageFactory], List[pystac.Item]],
        storage_factory: StorageFactory,
        collection_id: str,
        skip_validation: bool = False,
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        url = transform_url(message_data["url"])
        items = create_items_function(url, storage_factory)

        if collection_id:
            for item in items:
                item.collection_id = collection_id

        # TODO: refactor item validation
        # if not skip_validation:
        #     for item in items:
        #         validate_item(item)
        return items

    def process_message(
        self,
        message: azure.storage.queue.QueueMessage,
        cosmos_container_client: azure.cosmos.ContainerProxy,
        queue_client: azure.storage.queue.QueueClient,
        create_items_function: Callable[[str, StorageFactory], List[pystac.Item]],
        storage_factory: StorageFactory,
        collection_id: str,
    ) -> None:
        logger.info("Processing message id=%s", message.id)
        parsed_message = json.loads(message.content)
        try:
            items = self.create_items(
                parsed_message["data"],
                create_items_function=create_items_function,
                storage_factory=storage_factory,
                collection_id=collection_id,
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
                    cosmos_container_client.upsert_item(event)
                    logger.info("Persisted event id=%s", event["id"])

            # TODO: handle late deliveries, etc.
            logger.info("Processed message id=%s", message.id)
            queue_client.delete_message(message)

    def run(self, input: StreamingCreateItemsInput, context: TaskContext) -> NoOutput:
        create_items_function = input.create_items_function
        if isinstance(create_items_function, str):
            logger.info("Loading create_items_function")
            entrypoint = importlib.metadata.EntryPoint("", create_items_function, "")
            create_items_function = entrypoint.load()
        assert callable(create_items_function)

        logger.info("Starting task %s", type(self).__name__)

        logger.info("Getting azure credential")
        credential = azure.identity.DefaultAzureCredential()
        logger.info("Got azure credential")

        qc = azure.storage.queue.QueueClient.from_queue_url(
            input.queue_url, credential=credential
        )
        logger.info("Getting cosmos container client")
        db = (
            azure.cosmos.CosmosClient(input.cosmos_endpoint, credential)
            .get_database_client(input.db_name)
            .get_container_client(input.container_name)
        )
        logger.info("Got cosmos container client")

        while True:
            # Run forever, letting KEDA scale us down if necessary
            # need to update mypy
            for message in qc.receive_messages(  # type: ignore
                visibility_timeout=input.visibility_timeout
            ):
                self.process_message(
                    message=message,
                    cosmos_container_client=db,
                    queue_client=qc,
                    create_items_function=create_items_function,
                    storage_factory=context.storage_factory,
                    collection_id=input.collection_id,
                )
            # We've drained the queue. Now we'll pause slightly before checking again.
            # TODO: some kind of exponential backoff here. From 0 - 5-10 seconds.
            # I think after ~30 seconds of sleeping KEDA will stop this task.
            n = 5
            logger.info("Sleeping for %s seconds", n)
            time.sleep(n)


class StreamingIngestItemsInput(PCBaseModel):
    class Config:
        extra = "forbid"

    queue_url: str
    visibility_timeout: int
    min_replica_count: int = 0
    max_replica_count: int = 1
    polling_interval: int = 30
    trigger_queue_length: int = 100  # should this not have a default?
    collection_id: str


class StreamingIngestItemsTask(Task[StreamingIngestItemsInput, NoOutput]):
    _input_model = StreamingIngestItemsInput
    _output_model = NoOutput

    def process_message(
        self,
        message: azure.storage.queue.QueueMessage,
        queue_client: azure.storage.queue.QueueClient,
        pgstac: PgSTAC,
        collection_id: str,
    ) -> None:
        from pctasks.ingest_task.task import ingest_item

        item = json.loads(message.content)
        logger.info("Loading item")
        if collection_id:
            item["collection"] = collection_id
        ingest_item(pgstac, item)
        queue_client.delete_message(message)
        logger.info("Deleting message")

    def run(self, input: StreamingIngestItemsInput, context: TaskContext) -> NoOutput:
        from pctasks.ingest_task.task import PgSTAC

        pgstac = PgSTAC.from_env()

        credential = azure.identity.DefaultAzureCredential()
        qc = azure.storage.queue.QueueClient.from_queue_url(
            input.queue_url, credential=credential
        )

        while True:
            # Run forever, letting KEDA scale us down if necessary
            # TODO: We should batch these with messages_per_page
            # need to update mypy
            for message in qc.receive_messages(  # type: ignore
                visibility_timeout=input.visibility_timeout
            ):
                self.process_message(
                    message=message,
                    queue_client=qc,
                    pgstac=pgstac,
                    collection_id=input.collection_id,
                )
            # We've drained the queue. Now we'll pause slightly before checking again.
            # TODO: some kind of exponential backoff here. From 0 - 5-10 seconds.
            # I think after ~30 seconds of sleeping KEDA will stop this task.
            n = 5
            logger.info("Sleeping for %s seconds", n)
            time.sleep(n)


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
