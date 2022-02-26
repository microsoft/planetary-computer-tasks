from typing import Generic, TypeVar

from pydantic import BaseModel

from pctasks.core.models.base import PCBaseModel, RunRecordId

T = TypeVar("T", bound=BaseModel)


class ActivityMessage(Generic[T], PCBaseModel):
    run_record_id: RunRecordId
    msg: T
