from __future__ import annotations

import importlib.metadata
import logging
import traceback
from typing import Any, Callable, Dict, List, Tuple, Union

import azure.core.credentials
import azure.cosmos
import azure.identity
import azure.storage.queue
import pydantic
import pystac
from pystac.utils import str_to_datetime

from pctasks.core.cosmos.containers.create_item_errors import CreateItemErrorsContainer
from pctasks.core.cosmos.containers.items import ItemsContainer
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.event import (
    CreateItemErrorRecord,
    StorageEvent,
    StorageEventData,
)
from pctasks.core.models.item import ItemUpdatedRecord, StacItemRecord
from pctasks.core.models.task import WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.core.storage.blob import maybe_rewrite_blob_storage_url
from pctasks.dataset.items.task import validate_create_items_result
from pctasks.task.context import TaskContext
from pctasks.task.streaming import NoOutput, StreamingTaskMixin, StreamingTaskOptions
from pctasks.task.task import Task

logger = logging.getLogger("pctasks.dataset.streaming")

OK_T = List[Tuple[List[StacItemRecord], List[ItemUpdatedRecord]]]
ErrorsT = List[CreateItemErrorRecord]


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
    streaming_options: StreamingTaskOptions
        Settings for queue name, etc.
    collection_id: str
        The collection ID to set on the produced items. If the output of
        ``create_items`` has a collection ID, these must match.
    trigger_queue_length: int, default 100
        Controls the scaling factor.
    options: StreamingCreateItemsOptions
        Additional options for create items.
    create_items_function: str or callable.
        A callable or entrypoints-style path to a callable that creates the STAC
        item. This function will be called with the asset URI and a storage factory.
        It should return a list of pystac Items.
    extra_env: dict, optional
        Additional environment variables to set on the pod. This is primarily
        useful for testing, setting the ``AZURITE_HOST`` for example.
    """

    streaming_options: StreamingTaskOptions
    collection_id: str
    options: StreamingCreateItemsOptions = StreamingCreateItemsOptions()
    create_items_function: Union[
        str, Callable[[str, StorageFactory], List[pystac.Item]]
    ]
    extra_env: Dict[str, str] = pydantic.Field(default_factory=dict)

    class Config:
        extra = "forbid"


class StreamingCreateItemsTask(
    StreamingTaskMixin, Task[StreamingCreateItemsInput, NoOutput]
):
    """
    A streaming task for creating items.

    Notes
    -----
    This class relies on environment variables to configure the target
    Cosmos DB container to write created items to.

    - PCTASKS_COSMOSDB__URL: The URL to the Cosmos DB Account to use.

    See :meth:`pctasks.core.cosmos.containers.items.ItemsContainer`
    for more on how instances of this class get access to Cosmos DB.
    That class will use a connection string, account key, or a
    :class:`azure.identity.DefaultAzureCredential` to get the credentials.
    """

    _input_model = StreamingCreateItemsInput
    _output_model = NoOutput

    def get_required_environment_variables(self) -> List[str]:
        return ["PCTASKS_COSMOSDB__URL"]

    # Mypy doesn't like us using a more specific type for the input here.
    # I'm not sure what the solution is. You should only call this
    # method with the task type.
    def get_extra_options(  # type: ignore[override]
        self, input: StreamingCreateItemsInput, context: TaskContext
    ) -> Dict[str, Any]:
        items_record_container = ItemsContainer(StacItemRecord)
        items_update_container = ItemsContainer(ItemUpdatedRecord)
        create_item_errors_container = CreateItemErrorsContainer(CreateItemErrorRecord)

        create_items_function = input.create_items_function
        if isinstance(create_items_function, str):
            logger.info("Loading create_items_function")
            entrypoint = importlib.metadata.EntryPoint("", create_items_function, "")
            create_items_function = entrypoint.load()
        assert callable(create_items_function)

        items_record_container.__enter__()
        items_update_container.__enter__()
        create_item_errors_container.__enter__()

        logger.info("Writing STAC items to %s", items_record_container.name)
        logger.info("Writing Update records to %s", items_update_container.name)

        return {
            "items_containers": (
                items_record_container,
                items_update_container,
                create_item_errors_container,
            ),
            "create_items_function": create_items_function,
        }

    def cleanup(self, extra_options: Dict[str, Any]) -> None:
        (
            items_record_container,
            items_update_container,
            create_item_errors_container,
        ) = extra_options["items_containers"]
        items_record_container.__exit__(None, None, None)
        items_update_container.__exit__(None, None, None)
        create_item_errors_container.__exit__(None, None, None)

    def create_items(
        self,
        message_data: StorageEventData,
        create_items_function: Callable[[str, StorageFactory], List[pystac.Item]],
        storage_factory: StorageFactory,
        collection_id: str,
        skip_validation: bool = False,
    ) -> Union[List[pystac.Item], WaitTaskResult]:
        url = message_data.url
        # Transform event-grid https:// urls to blob:// urls
        url = maybe_rewrite_blob_storage_url(url)
        logger.info("Processing url %s", url)

        items = create_items_function(url, storage_factory)
        items = validate_create_items_result(
            items, collection_id=collection_id, skip_validation=skip_validation
        )

        return items

    # mypy doesn't like the child bringing in extra arguments, which is fair.
    # We can't get these off `input` though, unless it were
    # to cache the stuff.
    def process_message(  # type: ignore
        self,
        message: azure.storage.queue.QueueMessage,
        input: StreamingCreateItemsInput,
        context: TaskContext,
        items_containers: Tuple[
            ItemsContainer[StacItemRecord],
            ItemsContainer[ItemUpdatedRecord],
            CreateItemErrorsContainer,
        ],
        create_items_function: Callable[[str, StorageFactory], List[pystac.Item]],
    ) -> Tuple[OK_T, ErrorsT]:
        logger.info("Processing message id=%s", message.id)
        parsed_message = StorageEvent.parse_raw(message.content)
        if not callable(input.create_items_function):
            # Why isn't this already done?
            logger.info("Loading create_items_function")
            entrypoint = importlib.metadata.EntryPoint(
                "", input.create_items_function, ""
            )
            input.create_items_function = entrypoint.load()
        assert callable(
            input.create_items_function
        )  # convince mypy that this is the function.
        create_items_function = input.create_items_function
        ok: OK_T = []
        errors: ErrorsT = []

        try:
            items = self.create_items(
                parsed_message.data,
                create_items_function=create_items_function,
                storage_factory=context.storage_factory,
                collection_id=input.collection_id,
            )
        except Exception:
            logger.exception("Error in create item")
            error = CreateItemErrorRecord(
                type=parsed_message.type,
                spec_version=parsed_message.spec_version,
                source=parsed_message.source,
                subject=parsed_message.subject,
                id=parsed_message.id,
                time=parsed_message.time,
                data_content_type=parsed_message.data_content_type,
                data=parsed_message.data,
                run_id=context.run_id,
                traceback=traceback.format_exc(),
                dequeue_count=message.dequeue_count,
            )
            errors.append(error)
        else:
            if isinstance(items, WaitTaskResult):
                # This idealy won't happen in practice. Ideally the event
                # grid subscriptions are written such that they're only sent
                # when we're ready to process the item.
                raise Exception("Unexpected WaitTaskResult")
            else:
                item_records: List[StacItemRecord] = []
                update_records: List[ItemUpdatedRecord] = []

                for item in items:
                    logger.info("Created item id=%s", item.id)
                    item_record = StacItemRecord.from_item(item)
                    item_records.append(item_record)

                    update_records.append(
                        ItemUpdatedRecord(
                            stac_id=item_record.stac_id,
                            version=item_record.version,
                            run_id=context.run_id,
                            storage_event_time=str_to_datetime(parsed_message.time),
                            message_inserted_time=message.inserted_on,
                        )
                    )

                ok.append((item_records, update_records))
        return ok, errors

    def finalize_message(
        self,
        ok: OK_T,
        errors: ErrorsT,
        extra_options: Dict[str, Any],
    ) -> None:
        """
        Finalize processing of a message.

        This handles all of the I/O components, including

        1. Writing successes to the items and updates containers
        2. Writing errors to the errors container
        """
        (
            items_record_container,
            items_update_container,
            create_item_errors_container,
        ) = extra_options["items_containers"]

        for item_records, update_records in ok:
            items_record_container.bulk_put(item_records)
            items_update_container.bulk_put(update_records)
        for error in errors:
            create_item_errors_container.put(error)
        logger.info("Persisted records.")


def create_item_from_item_uri(
    asset_uri: str, storage_factory: StorageFactory
) -> Union[List[pystac.Item], WaitTaskResult]:
    """
    Create a STAC item from a file containing the STAC metadata.

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


def create_item_from_message(
    asset_uri: Dict[str, Any], storage_factory: StorageFactory
) -> Union[List[pystac.Item], WaitTaskResult]:
    # Just shoving the STAC item in the "url" field of the message.
    return [pystac.Item.from_dict(asset_uri)]
