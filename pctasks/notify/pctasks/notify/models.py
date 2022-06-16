from typing import List, Optional

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.event import CloudEvent, NotificationMessage
from pctasks.core.models.registration import (
    EventGridChannelInfo,
    STACItemEventRegistration,
)


class NotifyFetchMessage(PCBaseModel):
    notification: NotificationMessage
    target_environment: Optional[str] = None


class NotifyFetchResult(PCBaseModel):
    registrations: List[STACItemEventRegistration]


class NotifyWebhookMessage(PCBaseModel):
    endpoint: str
    event: CloudEvent


class NotifyEventGridChannelMessage(PCBaseModel):
    channel_info: EventGridChannelInfo
    event: CloudEvent


class NotifyResult(PCBaseModel):
    success: bool = True
