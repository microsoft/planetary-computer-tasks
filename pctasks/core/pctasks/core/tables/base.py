import json
import unicodedata
from base64 import b64decode, b64encode
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, Type, TypeVar

from azure.core.credentials import AzureNamedKeyCredential, AzureSasCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableClient, TableEntity, TableServiceClient
from pydantic.main import BaseModel

from pctasks.core.models.config import TableSasConfig

T = TypeVar("T", bound="TableService")
M = TypeVar("M", bound=BaseModel)
V = TypeVar("V")

PROHIBITED_TABLE_KEY_CHARS = ["/", "\\", "#", "?"]


class TableError(Exception):
    pass


class InvalidTableKeyError(Exception):
    INFO_MESSAGE = (
        "must not have any control characters or any or "
        "the following characters: "
        f"{', '.join(PROHIBITED_TABLE_KEY_CHARS)}"
    )
    pass

    @classmethod
    def from_key(cls, key: str) -> "InvalidTableKeyError":
        raise cls(f"Invalid table key: {key}. " f"Key {cls.INFO_MESSAGE}")


def encode_model(m: BaseModel) -> str:
    return b64encode(m.json(exclude_none=True).encode("utf-8")).decode("utf-8")


def decode_dict(s: str) -> Dict[str, Any]:
    return json.loads(b64decode(s.encode("utf-8")).decode("utf-8"))


def validate_table_key(table_key: str) -> None:
    valid = True
    for char in PROHIBITED_TABLE_KEY_CHARS:
        if char in table_key:
            valid = False
        if unicodedata.category(char)[0] == "C":
            valid = False
    if not valid:
        raise InvalidTableKeyError.from_key(table_key)


class TableService:
    def __init__(
        self,
        get_clients: Callable[[], Tuple[Optional[TableServiceClient], TableClient]],
    ) -> None:
        self._get_clients = get_clients
        self._service_client: Optional[TableServiceClient] = None
        self._table_client: Optional[TableClient] = None

    def _ensure_table_client(self) -> None:
        if not self._table_client:
            raise TableError("Table client not initialized. Use as a context manager.")

    def __enter__(self: T) -> T:
        self._service_client, self._table_client = self._get_clients()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._table_client:
            self._table_client.close()
            self._table_client = None
        if self._service_client:
            self._service_client.close()
            self._service_client = None

    @classmethod
    def from_sas_token(
        cls: Type[T], account_url: str, sas_token: str, table_name: str
    ) -> T:
        def _get_clients(
            _url: str = account_url, _token: str = sas_token, _table: str = table_name
        ) -> Tuple[Optional[TableServiceClient], TableClient]:
            table_service_client = TableServiceClient(
                endpoint=_url,
                credential=AzureSasCredential(_token),
            )
            return (
                table_service_client,
                table_service_client.get_table_client(table_name=_table),
            )

        return cls(_get_clients)

    @classmethod
    def from_connection_string(
        cls: Type[T], connection_string: str, table_name: str
    ) -> T:
        def _get_clients(
            _conn_str: str = connection_string, _table: str = table_name
        ) -> Tuple[Optional[TableServiceClient], TableClient]:
            table_service_client = TableServiceClient.from_connection_string(
                conn_str=_conn_str
            )
            return (
                table_service_client,
                table_service_client.get_table_client(table_name=_table),
            )

        return cls(_get_clients)

    @classmethod
    def from_account_key(
        cls: Type[T],
        account_name: str,
        account_key: str,
        table_name: str,
        account_url: Optional[str] = None,
    ) -> T:
        def _get_clients(
            _name: str = account_name,
            _key: str = account_key,
            _url: str = account_url or f"https://{account_name}.table.core.windows.net",
            _table: str = table_name,
        ) -> Tuple[Optional[TableServiceClient], TableClient]:
            credential = AzureNamedKeyCredential(name=_name, key=_key)
            table_service_client = TableServiceClient(
                endpoint=_url, credential=credential
            )
            return (
                table_service_client,
                table_service_client.get_table_client(table_name=_table),
            )

        return cls(_get_clients)

    @classmethod
    def from_config(cls: Type[T], config: TableSasConfig) -> T:
        return cls.from_sas_token(
            account_url=config.account_url,
            sas_token=config.sas_token,
            table_name=config.table_name,
        )


class ValueTableService(Generic[V], TableService):
    _type: Type[V]

    def insert(self, partition_key: str, row_key: str, value: V) -> None:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.create_entity(
            {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Value": value,
            }
        )

    def upsert(self, partition_key: str, row_key: str, value: V) -> None:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.upsert_entity(
            {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Value": value,
            }
        )

    def update(self, partition_key: str, row_key: str, value: V) -> None:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.update_entity(
            {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Value": value,
            }
        )

    def get(self, partition_key: str, row_key: str) -> Optional[V]:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        try:
            entity = self._table_client.get_entity(
                partition_key=partition_key, row_key=row_key
            )
            value: Any = entity.get("Value")
            if not value:
                raise TableError(
                    "Value column expected but not found. "
                    f"partition_key={partition_key} row_key={row_key}"
                )
            if not isinstance(value, self._type):
                raise TableError(
                    "Value column must be a string. "
                    f"partition_key={partition_key} row_key={row_key}"
                )
            return value
        except ResourceNotFoundError:
            return None


class StrTableService(TableService):
    _columns: List[str]

    def _validate_values(self, values: Dict[str, str]) -> None:
        if set(values) != set(self._columns):
            raise ValueError(
                "Values don't match columns. "
                f"values: {set(values.keys())} columns: {set(self._columns)}"
            )

    def insert(self, partition_key: str, row_key: str, values: Dict[str, str]) -> None:
        self._ensure_table_client()
        self._validate_values(values)
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.create_entity(
            {"PartitionKey": partition_key, "RowKey": row_key, **values}
        )

    def upsert(self, partition_key: str, row_key: str, values: Dict[str, str]) -> None:
        self._ensure_table_client()
        self._validate_values(values)
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.upsert_entity(
            {"PartitionKey": partition_key, "RowKey": row_key, **values}
        )

    def update(self, partition_key: str, row_key: str, values: Dict[str, str]) -> None:
        self._ensure_table_client()
        self._validate_values(values)
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.update_entity(
            {"PartitionKey": partition_key, "RowKey": row_key, **values}
        )

    def get(
        self, partition_key: str, row_key: str
    ) -> Optional[Dict[str, Optional[str]]]:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        try:
            entity = self._table_client.get_entity(
                partition_key=partition_key, row_key=row_key
            )
            if not entity:
                return None
            return {column: entity.get(column) for column in self._columns}
        except ResourceNotFoundError:
            return None


class ModelTableService(Generic[M], TableService):
    _model: Type[M]

    def _model_from_entity(self, entity: TableEntity) -> M:
        data: Any = entity.get("Data")
        if not data:
            partition_key = entity.get("PartitionKey")
            row_key = entity.get("RowKey")
            raise TableError(
                "Data column expected but not found. "
                f"partition_key={partition_key} row_key={row_key}"
            )
        if not isinstance(data, str):
            partition_key = entity.get("PartitionKey")
            row_key = entity.get("RowKey")
            raise TableError(
                "Data column must be a string. "
                f"partition_key={partition_key} row_key={row_key}"
            )
        return self._model.parse_obj(decode_dict(data))

    def insert(self, partition_key: str, row_key: str, entity: M) -> None:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.create_entity(
            {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Data": encode_model(entity),
            }
        )

    def upsert(self, partition_key: str, row_key: str, entity: M) -> None:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.upsert_entity(
            {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Data": encode_model(entity),
            }
        )

    def update(self, partition_key: str, row_key: str, entity: M) -> None:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.update_entity(
            {
                "PartitionKey": partition_key,
                "RowKey": row_key,
                "Data": encode_model(entity),
            }
        )

    def delete(self, partition_key: str, row_key: str) -> None:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        self._table_client.delete_entity(partition_key=partition_key, row_key=row_key)

    def get(self, partition_key: str, row_key: str) -> Optional[M]:
        self._ensure_table_client()
        validate_table_key(partition_key)
        validate_table_key(row_key)
        assert self._table_client
        try:
            entity = self._table_client.get_entity(
                partition_key=partition_key, row_key=row_key
            )
            return self._model_from_entity(entity)
        except ResourceNotFoundError:
            return None

    def fetch_all(self) -> List[M]:
        self._ensure_table_client()
        assert self._table_client
        return [
            self._model_from_entity(entity)
            for entity in self._table_client.list_entities()
        ]

    def query(self, q: str) -> List[M]:
        self._ensure_table_client()
        assert self._table_client
        result = []
        for entity in self._table_client.query_entities(q):
            try:

                result.append(self._model_from_entity(entity))
            except Exception as e:
                print((entity["PartitionKey"], entity["RowKey"]))
                print(e)
        return result
