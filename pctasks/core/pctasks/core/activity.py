import logging
from typing import Callable, Type, TypeVar

import orjson
from pydantic import BaseModel, ValidationError

from pctasks.core.logging import RunLogger
from pctasks.core.models.activity import ActivityMessage
from pctasks.core.models.base import PCBaseModel, RunRecordId
from pctasks.core.utils import StrEnum

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=PCBaseModel)

logger = logging.getLogger(__name__)


class ActivityStatus(StrEnum):
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_SENT = "message_received"
    FAILED = "failed"


def wrap_activity(
    activity: Callable[[T, RunLogger], U], model_class: Type[T], activity_name: str
) -> Callable[[str], str]:
    """Wraps a function to be used as an Azure Durable Function activity."""

    def _func(msg: str) -> str:
        msg_dict = orjson.loads(msg)
        if "msg" not in msg_dict:
            raise ValueError(f"Missing 'msg' in message: {msg_dict}")

        activity_msg: ActivityMessage[T] = ActivityMessage(
            run_record_id=RunRecordId.parse_obj(msg_dict.get("run_record_id")),
            msg=model_class.parse_obj(msg_dict["msg"]),
        )

        event_logger = RunLogger(activity_msg.run_record_id, logger_id=activity_name)
        event_logger.log_event(ActivityStatus.MESSAGE_RECEIVED)
        try:
            result = activity(activity_msg.msg, event_logger)
            event_logger.log_event(ActivityStatus.MESSAGE_SENT)
            return result.json()
        except ValidationError as e:
            logger.exception(e)
            event_logger.log_event(
                ActivityStatus.FAILED, message=f"Failed to parse message: {e}"
            )
            raise
        except Exception as e:
            logger.exception(e)
            event_logger.log_event(
                ActivityStatus.FAILED, message=f"Failed to process message: {e}"
            )
            raise

    return _func
