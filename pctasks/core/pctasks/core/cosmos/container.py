import logging
from abc import ABC, abstractmethod
from enum import Enum
from itertools import groupby
from typing import (
    Any,
    AsyncIterable,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import orjson
from azure.core.async_paging import AsyncItemPaged, AsyncPageIterator
from azure.core.paging import ItemPaged, PageIterator
from azure.cosmos import ContainerProxy
from azure.cosmos.aio import ContainerProxy as AsyncContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from pydantic import BaseModel

from pctasks.core.cosmos.database import (
    AsyncCosmosDBClients,
    CosmosDBClients,
    CosmosDBDatabase,
)
from pctasks.core.cosmos.page import Page
from pctasks.core.cosmos.settings import CosmosDBSettings
from pctasks.core.models.run import Record
from pctasks.core.models.utils import tzutc_now
from pctasks.core.utils import grouped
from pctasks.core.utils.backoff import BackoffStrategy, with_backoff, with_backoff_async

T = TypeVar("T", bound=Record)

logger = logging.getLogger(__name__)


class ContainerOperation(Enum):
    PUT = "PUT"
    BULK_PUT = "BULK_PUT"
    GET = "GET"
    QUERY = "QUERY"


class TriggerType(Enum):
    PRE = "pre"
    POST = "post"


def query_clean(s: str) -> str:
    return s.replace("\n", " ").replace("\t", " ").strip()


class BaseCosmosDBContainer(Generic[T], ABC):
    def __init__(
        self,
        name: Union[str, Callable[[CosmosDBSettings], str]],
        partition_key: str,
        model_type: Type[T],
        db: Optional[CosmosDBDatabase] = None,
        settings: Optional[CosmosDBSettings] = None,
        stored_procedures: Optional[
            Dict[ContainerOperation, Dict[Type[BaseModel], str]]
        ] = None,
        triggers: Optional[Dict[ContainerOperation, Dict[TriggerType, str]]] = None,
        with_backoff_waits: Optional[List[float]] = None,
    ) -> None:
        if not settings:
            if db:
                settings = db.settings
            else:
                settings = CosmosDBSettings.get()
        if not db:
            db = CosmosDBDatabase(settings)
        self.settings = settings
        self.db = db
        self.partition_key = partition_key
        self.model_type = model_type
        if callable(name):
            name = name(settings)
        self.name = name
        self.stored_procedures = stored_procedures
        self.triggers = triggers

        self.backoff_strategy = BackoffStrategy(
            waits=with_backoff_waits
            or [
                0.1,
                0.2,
                0.3,
                0.4,
                0.5,
                1,
                2,
                5,
                10,
            ]
        )

    @abstractmethod
    def get_partition_key(self, model: T) -> str:
        ...

    def get_trigger(
        self, operation: ContainerOperation, trigger_type: TriggerType
    ) -> Optional[str]:
        """Returns the ID of a trigger if one exists."""
        if not self.triggers:
            return None
        return self.triggers.get(operation, {}).get(trigger_type)

    def item_from_model(self, model: T) -> Dict[str, Any]:
        """Transform a model into a cosmosdb item (dict)."""
        result = orjson.loads(model.json())
        if "id" not in result:
            result["id"] = model.get_id()
        return result

    def model_from_item(self, model_type: Type[T], item: Dict[str, Any]) -> T:
        """Transform a cosmosdb item (dict) into a model."""
        return model_type.parse_obj(item)

    def _prepare_put_item(self, model: T) -> Dict[str, Any]:
        # Set created or updated time
        if not model.created:
            model.created = tzutc_now()
        else:
            model.updated = tzutc_now()

        # Get the JSON representation of the model
        item = self.item_from_model(model)

        # If no ID is set, get the ID from the model
        if "id" not in item:
            item["id"] = model.get_id()

        return item

    def _get_put_stored_proc(self, model: T) -> Optional[str]:
        stored_proc: Optional[str] = None
        if self.stored_procedures:
            stored_proc = self.stored_procedures.get(ContainerOperation.PUT, {}).get(
                type(model)
            )

        return stored_proc

    def _get_bulk_put_stored_proc(self, model: T) -> Optional[str]:
        stored_proc: Optional[str] = None
        if self.stored_procedures:
            stored_proc = self.stored_procedures.get(
                ContainerOperation.BULK_PUT, {}
            ).get(type(model))

        return stored_proc

    def _group_for_bulk_put(
        self, models: Iterable[T]
    ) -> Iterable[Tuple[str, List[Dict[str, Any]]]]:
        by_partition_key = groupby(models, key=self.get_partition_key)
        for partition_key, partition_models in by_partition_key:
            items = [self._prepare_put_item(model) for model in partition_models]
            # Bulk put the items in groups of the max size
            for item_group in grouped(items, self.settings.max_bulk_put_size):
                yield partition_key, list(item_group)

    def _query_prep(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, Optional[List[Dict[str, Any]]]]:
        params: Optional[List[Dict[str, Any]]] = None
        if parameters:
            params = [
                {"name": k if k.startswith("@") else f"@{k}", "value": query_clean(v)}
                for k, v in parameters.items()
            ]

        return query_clean(query), params


class CosmosDBContainer(BaseCosmosDBContainer[T], ABC):
    def __init__(
        self,
        name: Union[str, Callable[[CosmosDBSettings], str]],
        partition_key: str,
        model_type: Type[T],
        db: Optional[CosmosDBDatabase] = None,
        settings: Optional[CosmosDBSettings] = None,
        stored_procedures: Optional[
            Dict[ContainerOperation, Dict[Type[BaseModel], str]]
        ] = None,
        triggers: Optional[Dict[ContainerOperation, Dict[TriggerType, str]]] = None,
    ) -> None:

        self.cosmos_clients: Optional[CosmosDBClients] = None
        super().__init__(
            name,
            partition_key,
            model_type,
            db=db,
            settings=settings,
            stored_procedures=stored_procedures,
            triggers=triggers,
        )

    def __enter__(self) -> "CosmosDBContainer[T]":
        self.cosmos_clients = self.db.create_clients(self.name)
        return self

    def __exit__(self, *args: Any) -> None:
        if self.cosmos_clients:
            self.cosmos_clients.close()
            self.cosmos_clients = None

    def _ensure_clients(self) -> None:
        if not self.cosmos_clients:
            raise ValueError(
                "Container clients not initialized. Use as context manager."
            )

    @property
    def _container_client(self) -> ContainerProxy:
        self._ensure_clients()
        assert self.cosmos_clients
        return self.cosmos_clients.container

    def put(self, model: T) -> None:
        item = self._prepare_put_item(model)
        stored_proc = self._get_put_stored_proc(model)

        if stored_proc:
            partition_key = self.get_partition_key(model)
            sp_name: str = stored_proc
            with_backoff(
                lambda: self._container_client.scripts.execute_stored_procedure(
                    sp_name, partition_key=partition_key, parameters=[item]
                ),
                strategy=self.backoff_strategy,
            )
        else:
            # Otherwise upsert the item
            self._container_client.upsert_item(
                item,
                pre_trigger_include=self.get_trigger(
                    ContainerOperation.PUT, TriggerType.PRE
                ),
                post_trigger_include=self.get_trigger(
                    ContainerOperation.PUT, TriggerType.POST
                ),
            )

    def bulk_put(self, models: Iterable[T]) -> None:
        if not models:
            return
        models = list(models)
        stored_proc = self._get_bulk_put_stored_proc(models[0])
        if not stored_proc:
            logger.warning(
                f"No bulk put stored procedure for {self.name} "
                f"and model {type(models[0])}. Falling back to individual puts."
            )
            for model in models:
                with_backoff(lambda: self.put(model))
        else:
            for partition_key, item_group in self._group_for_bulk_put(models):
                sp_name: str = stored_proc
                with_backoff(
                    lambda: self._container_client.scripts.execute_stored_procedure(
                        sp_name,
                        partition_key=partition_key,
                        params=[list(item_group)],
                    ),
                    strategy=self.backoff_strategy,
                )

    def get(self, id: str, partition_key: str) -> Optional[T]:
        try:
            item = with_backoff(
                lambda: self._container_client.read_item(
                    id, partition_key=partition_key
                ),
                strategy=self.backoff_strategy,
            )
        except CosmosResourceNotFoundError:
            return None
        if item.get("deleted"):
            return None

        return self.model_from_item(self.model_type, item)

    def query_paged(
        self,
        partition_key: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        continuation_token: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> Iterable[Page[T]]:
        query, params = self._query_prep(query, parameters)

        item_paged = cast(
            ItemPaged[Dict[str, Any]],
            with_backoff(
                lambda: self._container_client.query_items(
                    query=query,
                    parameters=params,
                    partition_key=partition_key,
                    max_item_count=page_size,
                ),
                strategy=self.backoff_strategy,
            ),
        )

        # Loop over the pages while yielding results,
        # applying a with_backoff to each page request.

        paged_iterator = cast(
            PageIterator[Dict[str, Any]],
            with_backoff(
                lambda: item_paged.by_page(continuation_token=continuation_token)
            ),
        )

        def _next_page() -> Optional[Iterator[Dict[str, Any]]]:
            try:
                return next(paged_iterator)
            except StopIteration:
                return None

        while True:
            page = with_backoff(
                _next_page,
                strategy=self.backoff_strategy,
            )

            if not page:
                break

            # Paged iterator mutates the continuation token property
            # after each page fetch.
            continuation_token = paged_iterator.continuation_token

            yield Page(
                items=map(
                    lambda item: self.model_from_item(self.model_type, item), page
                ),
                continuation_token=continuation_token,
            )

    def query(
        self,
        partition_key: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Iterable[T]:
        for page in self.query_paged(partition_key, query, parameters=parameters):
            for item in page:
                yield item

    def query_across_partitions_unsafe(self, query: str) -> Iterable[T]:
        return map(
            lambda item: self.model_from_item(self.model_type, item),
            self._container_client.query_items(
                query=query, enable_cross_partition_query=True
            ),
        )


class AsyncCosmosDBContainer(BaseCosmosDBContainer[T], ABC):
    def __init__(
        self,
        name: Union[str, Callable[[CosmosDBSettings], str]],
        partition_key: str,
        model_type: Type[T],
        db: Optional[CosmosDBDatabase] = None,
        settings: Optional[CosmosDBSettings] = None,
        stored_procedures: Optional[
            Dict[ContainerOperation, Dict[Type[BaseModel], str]]
        ] = None,
        triggers: Optional[Dict[ContainerOperation, Dict[TriggerType, str]]] = None,
    ) -> None:

        self.cosmos_clients: Optional[AsyncCosmosDBClients] = None
        super().__init__(
            name,
            partition_key,
            model_type,
            db=db,
            settings=settings,
            stored_procedures=stored_procedures,
            triggers=triggers,
        )

    async def __aenter__(self) -> "AsyncCosmosDBContainer[T]":
        self.cosmos_clients = self.db.create_async_clients(self.name)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self.cosmos_clients:
            await self.cosmos_clients.close()
            self.cosmos_clients = None

    def _ensure_clients(self) -> None:
        if not self.cosmos_clients:
            raise ValueError(
                "Container clients not initialized. Use as context manager."
            )

    @property
    def _container_client(self) -> AsyncContainerProxy:
        self._ensure_clients()
        assert self.cosmos_clients
        return self.cosmos_clients.container

    async def put(self, model: T) -> None:
        item = self._prepare_put_item(model)
        stored_proc = self._get_put_stored_proc(model)

        if stored_proc:
            sp_name: str = stored_proc
            partition_key = self.get_partition_key(model)

            async def _sp() -> Dict[str, Any]:
                return await self._container_client.scripts.execute_stored_procedure(
                    sp_name, partition_key=partition_key, parameters=[item]
                )

            await with_backoff_async(
                _sp,
                strategy=self.backoff_strategy,
            )
        else:
            # Otherwise upsert the item
            async def _upsert() -> Dict[str, Any]:
                return await self._container_client.upsert_item(
                    item,
                    pre_trigger_include=self.get_trigger(
                        ContainerOperation.PUT, TriggerType.PRE
                    ),
                    post_trigger_include=self.get_trigger(
                        ContainerOperation.PUT, TriggerType.POST
                    ),
                )

            await with_backoff_async(
                _upsert,
                strategy=self.backoff_strategy,
            )

    async def bulk_put(self, models: Iterable[T]) -> None:
        if not models:
            return
        models = list(models)
        stored_proc = self._get_bulk_put_stored_proc(models[0])
        if not stored_proc:
            logger.warning(
                f"No bulk put stored procedure for {self.name} "
                f"and model {type(models[0])}. Falling back to individual puts."
            )
            for model in models:
                await self.put(model)
        else:
            sp_name: str = stored_proc
            for partition_key, item_group in self._group_for_bulk_put(models):

                async def _sp() -> Dict[str, Any]:
                    return (
                        await self._container_client.scripts.execute_stored_procedure(
                            sp_name,
                            partition_key=partition_key,
                            params=[list(item_group)],
                        )
                    )

                await with_backoff_async(
                    _sp,
                    strategy=self.backoff_strategy,
                )

    async def get(self, id: str, partition_key: str) -> Optional[T]:
        try:

            async def _read() -> Dict[str, Any]:
                return await self._container_client.read_item(
                    id, partition_key=partition_key
                )

            item = await with_backoff_async(
                _read,
                strategy=self.backoff_strategy,
            )
        except CosmosResourceNotFoundError:
            return None
        if item.get("deleted"):
            return None

        return self.model_from_item(self.model_type, item)

    async def query_paged(
        self,
        partition_key: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        continuation_token: Optional[str] = None,
        page_size: Optional[int] = None,
    ) -> AsyncIterable[Page[T]]:
        query, params = self._query_prep(query, parameters)

        item_paged = cast(
            AsyncItemPaged[Dict[str, Any]],
            self._container_client.query_items(
                query=query,
                parameters=params,
                partition_key=partition_key,
                max_item_count=page_size,
            ),
        )

        # Loop over the pages while yielding results,
        # applying a with_backoff to each page request.

        paged_iterator = cast(
            AsyncPageIterator[Dict[str, Any]],
            item_paged.by_page(continuation_token=continuation_token),
        )

        async def _next_page() -> Optional[AsyncIterator[Dict[str, Any]]]:
            try:
                return await paged_iterator.__anext__()
            except StopAsyncIteration:
                return None

        while True:
            page = await with_backoff_async(_next_page, strategy=self.backoff_strategy)
            if not page:
                break

            # Paged iterator mutates the continuation token property
            # after each page fetch.
            continuation_token = paged_iterator.continuation_token

            yield Page(
                items=[
                    self.model_from_item(self.model_type, item) async for item in page
                ],
                continuation_token=continuation_token,
            )

    async def query(
        self,
        partition_key: str,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterable[T]:
        async for page in self.query_paged(partition_key, query, parameters=parameters):
            for item in page:
                yield item

    async def query_across_partitions_unsafe(self, query: str) -> AsyncIterable[T]:
        async for item in self._container_client.query_items(
            query=query, enable_cross_partition_query=True
        ):
            yield self.model_from_item(self.model_type, item)
