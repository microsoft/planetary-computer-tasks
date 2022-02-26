from typing import Any, Dict

from pctasks.core.message_handler import MessageHandler
from pctasks.core.models.dataset import (
    CreateDatasetOperation,
    DatasetIdentifier,
    DatasetOperation,
    DatasetOperationSubmitMessage,
    DeleteDatasetOperation,
    UpdateDatasetOperation,
)
from pctasks.operations.settings import OperationsSettings


def create_dataset(dataset: DatasetIdentifier) -> None:
    settings = OperationsSettings.get()
    with settings.get_dataset_table() as table:
        table.create_dataset(dataset)


def update_dataset(dataset: DatasetIdentifier) -> None:
    settings = OperationsSettings.get()
    with settings.get_dataset_table() as table:
        table.create_dataset(dataset)


def delete_dataset(dataset: DatasetIdentifier) -> None:
    settings = OperationsSettings.get()
    with settings.get_dataset_table() as table:
        table.create_dataset(dataset)


class DatasetOperationHandler(MessageHandler):
    def handle(self, message: Dict[str, Any]) -> None:
        submit_msg = DatasetOperationSubmitMessage.parse_obj(message)
        operation: DatasetOperation = submit_msg.operation
        if isinstance(operation, CreateDatasetOperation):
            create_dataset(operation.dataset)
        elif isinstance(operation, UpdateDatasetOperation):
            update_dataset(operation.dataset)
        elif isinstance(operation, DeleteDatasetOperation):
            delete_dataset(operation.dataset)
        else:
            raise ValueError(f"Unknown operation: {operation}")
