import re
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import Field, model_validator
from typing_extensions import Self

from pctasks.core.constants import MICROSOFT_OWNER
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.event import CloudEvent
from pctasks.core.models.workflow import WorkflowDefinition


class EventFilter(PCBaseModel):
    subject_matches: Optional[str]
    source_matches: Optional[str]

    def matches(self, event: CloudEvent) -> bool:
        if self.subject_matches:
            if not event.subject:
                return False
            if not re.match(self.subject_matches, event.subject):
                return False
        if self.source_matches:
            if not re.match(self.source_matches, event.source):
                return False
        return True


class GeometryEventFilter(EventFilter):
    area_of_interest: Optional[Dict[str, Any]]

    def matches(self, event: CloudEvent) -> bool:
        if not super().matches(event):
            return False

        if self.area_of_interest:
            # TODO: Implement geometry filtering
            pass

        return True


class EventRegistration(PCBaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    owner_id: str = MICROSOFT_OWNER
    event_type: str
    event_filter: Optional[EventFilter] = None

    def matches(self, event: CloudEvent) -> bool:
        if self.event_type != event.type:
            return False
        if self.event_filter:
            f = self.event_filter
            if f.subject_matches:
                if not event.subject:
                    return False
                if not re.match(f.subject_matches, event.subject):
                    return False
            if f.source_matches:
                if not re.match(f.source_matches, event.source):
                    return False
        return True


class BlobTriggerEventRegistration(EventRegistration):
    storage_account: str
    container: str
    workflow: WorkflowDefinition

    def matches(self, event: CloudEvent) -> bool:
        if self.event_type != event.type:
            return False
        if self.event_filter:
            f = self.event_filter
            if f.subject_matches:
                if not event.subject:
                    return False
                if not re.match(f.subject_matches, event.subject):
                    return False
            if f.source_matches:
                if not re.match(f.source_matches, event.source):
                    return False
        return True


class EventGridChannelInfo(PCBaseModel):
    # TODO
    channel_id: str


class STACItemEventRegistration(EventRegistration):
    id: str = Field(default_factory=lambda: str(uuid4()))
    owner_id: str = MICROSOFT_OWNER
    event_type: str
    collection_id: str
    event_filter: Optional[GeometryEventFilter] = None
    webhook_endpoint: Optional[str]
    eventgrid_channel_info: Optional[EventGridChannelInfo] = None

    def matches(self, event: CloudEvent) -> bool:
        if self.event_type != event.type:
            return False
        if self.event_filter:
            if not self.event_filter.matches(event):
                return False
        return True

    @model_validator(mode="after")
    def validate_eventgrid_channel_info(self) -> Self:
        if not self.eventgrid_channel_info and not self.webhook_endpoint:
            raise ValueError(
                "Either eventgrid_channel_info or webhook_endpoint must be set"
            )
        return self
