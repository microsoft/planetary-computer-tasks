from typing import Union

from pydantic import Field, validator

from pctasks.core.constants import DATASET_OPERATION_TARGET, MICROSOFT_OWNER
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.operation import OperationSubmitMessage
from pctasks.core.tables.base import InvalidTableKeyError, validate_table_key
from pctasks.core.utils import StrEnum


class DatasetIdentifier(PCBaseModel):
    owner: str = MICROSOFT_OWNER
    name: str

    def __str__(self) -> str:
        return f"{self.owner}/{self.name}"

    def as_key(self) -> str:
        return f"{self.owner}||{self.name}"

    @classmethod
    def from_string(cls, s: str) -> "DatasetIdentifier":
        split = s.split("/")
        if not len(split) == 2:
            raise ValueError(f"Invalid dataset identifier '{s}'")
        return cls(owner=split[0], name=split[1])

    @validator("owner")
    def _validate_owner(cls, v: str) -> str:
        try:
            validate_table_key(v)
        except InvalidTableKeyError as e:
            raise ValueError(f"Invalid owner '{v}': {e.INFO_MESSAGE}")
        return v

    @validator("name")
    def _validate_name(cls, v: str) -> str:
        try:
            validate_table_key(v)
        except InvalidTableKeyError as e:
            raise ValueError(f"Invalid name '{v}': {e.INFO_MESSAGE}")
        return v


class DatasetOperationType(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class DatasetOperation(PCBaseModel):
    type: str = Field(DatasetOperationType, const=True)


class CreateDatasetOperation(DatasetOperation):
    type: str = Field(default=DatasetOperationType.CREATE, const=True)
    dataset: DatasetIdentifier


class UpdateDatasetOperation(DatasetOperation):
    type: str = Field(default=DatasetOperationType.UPDATE, const=True)
    dataset: DatasetIdentifier


class DeleteDatasetOperation(DatasetOperation):
    type: str = Field(default=DatasetOperationType.DELETE, const=True)
    dataset: DatasetIdentifier


class DatasetOperationSubmitMessage(OperationSubmitMessage):
    operation: Union[
        CreateDatasetOperation, UpdateDatasetOperation, DeleteDatasetOperation
    ]
    target: str = Field(default=DATASET_OPERATION_TARGET, const=True)
