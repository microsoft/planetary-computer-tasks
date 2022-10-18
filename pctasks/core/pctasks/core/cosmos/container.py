from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Generic, Iterable, List, Optional, Type, TypeVar, cast

import orjson
from azure.core.paging import ItemPaged, PageIterator
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from pydantic import BaseModel

from pctasks.core.cosmos.database import CosmosDBDatabase
from pctasks.core.cosmos.page import Page
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


class CosmosDBContainer(Generic[T], ABC):
    def __init__(
        self,
        name: str,
        partition_key: str,
        model_type: Type[T],
        db: Optional[CosmosDBDatabase] = None,
        stored_procedures: Optional[
            Dict[ContainerOperation, Dict[Type[BaseModel], str]]
        ] = None,
        triggers: Optional[Dict[ContainerOperation, Dict[TriggerType, str]]] = None,
    ) -> None:
        if not db:
            db = CosmosDBDatabase()
        self.client = db
        self.name = name
        self.partition_key = partition_key
        self.model_type = model_type
        self.container_client = self.client.get_container_client(name)
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

    def put(self, model: T) -> None:
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
        if stored_proc:
            partition_key = self.get_partition_key(model)
            self.container_client.scripts.execute_stored_procedure(
                stored_proc, partition_key, [item]
            )
        else:
            # Otherwise upsert the item
            self.container_client.upsert_item(
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
            item = self.container_client.read_item(id, partition_key=partition_key)
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
        params: Optional[List[Dict[str, Any]]] = None
        if parameters:
            params = [
                {"name": k if k.startswith("@") else f"@{k}", "value": v}
                for k, v in parameters.items()
            ]

        item_paged = cast(
            ItemPaged[Dict[str, Any]],
            self.container_client.query_items(
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
            self.container_client.query_items(
                query=query, enable_cross_partition_query=True
            ),
        )
