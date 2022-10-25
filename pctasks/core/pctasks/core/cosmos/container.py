from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    Any,
    AsyncIterable,
    Callable,
    Dict,
    Generic,
    Iterable,
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

T = TypeVar("T", bound=Record)


class ContainerOperation(Enum):
    PUT = "PUT"
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
    ) -> None:
        if not settings:
            if db:
                settings = db.settings
            else:
                settings = CosmosDBSettings.get()
        if not db:
            db = CosmosDBDatabase(settings)
        self.db = db
        self.partition_key = partition_key
        self.model_type = model_type
        if callable(name):
            name = name(settings)
        self.name = name
        self.stored_procedures = stored_procedures
        self.triggers = triggers

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

    def _put_prep(self, model: T) -> Tuple[Dict[str, Any], Optional[str]]:
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

        # If a stored procedure is defined for this operation, use it
        stored_proc: Optional[str] = None
        if self.stored_procedures:
            stored_proc = self.stored_procedures.get(ContainerOperation.PUT, {}).get(
                type(model)
            )

        return item, stored_proc

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
        item, stored_proc = self._put_prep(model)

        if stored_proc:
            partition_key = self.get_partition_key(model)
            self._container_client.scripts.execute_stored_procedure(
                stored_proc, partition_key=partition_key, parameters=[item]
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

    def get(self, id: str, partition_key: str) -> Optional[T]:
        try:
            item = self._container_client.read_item(id, partition_key=partition_key)
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
            self._container_client.query_items(
                query=query,
                parameters=params,
                partition_key=partition_key,
                max_item_count=page_size,
            ),
        )
        paged_iterator = cast(
            PageIterator[Dict[str, Any]],
            item_paged.by_page(continuation_token=continuation_token),
        )
        for page in paged_iterator:
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
        item, stored_proc = self._put_prep(model)

        if stored_proc:
            partition_key = self.get_partition_key(model)
            await self._container_client.scripts.execute_stored_procedure(
                stored_proc, partition_key=partition_key, parameters=[item]
            )
        else:
            # Otherwise upsert the item
            await self._container_client.upsert_item(
                item,
                pre_trigger_include=self.get_trigger(
                    ContainerOperation.PUT, TriggerType.PRE
                ),
                post_trigger_include=self.get_trigger(
                    ContainerOperation.PUT, TriggerType.POST
                ),
            )

    async def get(self, id: str, partition_key: str) -> Optional[T]:
        try:
            item = await self._container_client.read_item(
                id, partition_key=partition_key
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
        paged_iterator = cast(
            AsyncPageIterator[Dict[str, Any]],
            item_paged.by_page(continuation_token=continuation_token),
        )
        async for page in paged_iterator:
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
