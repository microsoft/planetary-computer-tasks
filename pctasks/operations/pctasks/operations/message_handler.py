from typing import Any, Dict, Optional

from pctasks.core.constants import DATASET_OPERATION_TARGET
from pctasks.core.message_handler import MessageHandler, MessageHandlers
from pctasks.core.models.operation import OperationSubmitMessage
from pctasks.operations.dataset.handler import DatasetOperationHandler


def get_handler(message: Dict[str, Any]) -> Optional[MessageHandler]:
    submit_msg = OperationSubmitMessage.parse_obj(message)
    target_type = submit_msg.target
    if target_type is None:
        raise ValueError(f"No target type in message: {message}")
    if target_type == DATASET_OPERATION_TARGET:
        return DatasetOperationHandler()
    return None


HANDLERS = MessageHandlers(get_handler)
