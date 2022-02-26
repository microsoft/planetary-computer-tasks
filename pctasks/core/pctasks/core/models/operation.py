from uuid import uuid4

from pydantic import Field

from pctasks.core.constants import OPERATION_MESSAGE_TYPE
from pctasks.core.models.base import PCBaseModel


class OperationSubmitMessage(PCBaseModel):
    operation_id: str = Field(default_factory=lambda: uuid4().hex)
    type: str = Field(default=OPERATION_MESSAGE_TYPE, const=True)
    target: str
