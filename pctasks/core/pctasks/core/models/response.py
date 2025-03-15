"""Models for requests and responses to the PCTask API."""

from typing import Generic, Iterable, List, Optional, TypeVar

from pydantic import Field

from pctasks.core.cosmos.page import Page
from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.run import JobPartitionRunRecord, Record, WorkflowRunRecord
from pctasks.core.models.workflow import WorkflowRecord
from pctasks.core.utils import StrEnum

T = TypeVar("T", bound=Record)


class UploadCodeResult(PCBaseModel):
    uri: str


# Records responses
class LinkRel(StrEnum):
    JOB = "job"
    TASK = "task"
    LOG = "log"


class Link(PCBaseModel):
    rel: str
    href: str
    type: Optional[str] = None
    title: Optional[str] = None


class RecordResponse(Generic[T], PCBaseModel):
    links: Optional[List[Link]] = Field(default=[])
    record: T


class WorkflowRecordResponse(RecordResponse[WorkflowRecord]):
    record: WorkflowRecord


class WorkflowRunRecordResponse(RecordResponse[WorkflowRunRecord]):
    record: WorkflowRunRecord


class JobPartitionRunRecordResponse(RecordResponse[JobPartitionRunRecord]):
    record: JobPartitionRunRecord


class RecordListResponse(Generic[T], PCBaseModel):
    links: Optional[List[Link]] = Field(default=[])
    records: List[T]
    next_page_token: Optional[str] = Field(None, alias="nextPageToken")


class WorkflowRecordListResponse(RecordListResponse[WorkflowRecord]):
    records: List[WorkflowRecord]

    @classmethod
    def from_pages(
        cls, pages: Iterable[Page[WorkflowRecord]]
    ) -> "WorkflowRecordListResponse":
        try:
            page = next(pages.__iter__())
        except StopIteration:
            return cls(records=[], nextPageToken=None)

        return cls(records=list(page), nextPageToken=page.continuation_token)


class WorkflowRunRecordListResponse(RecordListResponse[WorkflowRunRecord]):
    records: List[WorkflowRunRecord]

    @classmethod
    def from_pages(
        cls, pages: Iterable[Page[WorkflowRunRecord]]
    ) -> "WorkflowRunRecordListResponse":
        try:
            page = next(pages.__iter__())
        except StopIteration:
            return cls(records=[], nextPageToken=None)

        return cls(records=list(page), nextPageToken=page.continuation_token)


class JobPartitionRunRecordListResponse(RecordListResponse[JobPartitionRunRecord]):
    records: List[JobPartitionRunRecord]

    @classmethod
    def from_pages(
        cls, pages: Iterable[Page[JobPartitionRunRecord]]
    ) -> "JobPartitionRunRecordListResponse":
        try:
            page = next(pages.__iter__())
        except StopIteration:
            return cls(records=[], nextPageToken=None)

        return cls(records=list(page), nextPageToken=page.continuation_token)
