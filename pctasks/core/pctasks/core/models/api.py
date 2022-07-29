"""Models for requests and responses to the PCTask API."""

from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.event import CloudEvent
from pctasks.core.models.record import (
    JobRunRecord,
    JobRunStatus,
    TaskRunRecord,
    WorkflowRunRecord,
)
from pctasks.core.models.workflow import WorkflowConfig, WorkflowRunStatus
from pctasks.core.utils import StrEnum


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


class RecordResponse(PCBaseModel):
    links: Optional[List[Link]] = None
    errors: Optional[List[str]] = None
    created: datetime
    updated: datetime
    status: str


class TaskRunResponse(RecordResponse):
    run_id: str
    job_id: str
    task_id: str

    status: str

    errors: Optional[List[str]] = None

    @classmethod
    def from_record(
        cls, record: TaskRunRecord, log_uri_to_href: Callable[[str], str]
    ) -> "TaskRunResponse":
        links: List[Link] = []
        if record.log_uris:
            for log_uri in record.log_uris:
                href = log_uri_to_href(log_uri)
                log_name = Path(log_uri).name
                links.append(
                    Link(
                        rel=LinkRel.LOG,
                        href=href,
                        type="text/plain",
                        title=f"Task log: {log_name}",
                    )
                )

        return cls(
            run_id=record.run_id,
            job_id=record.job_id,
            task_id=record.task_id,
            status=record.status,
            links=links,
            errors=record.errors,
            created=record.created,
            updated=record.updated,
        )


class TaskRunsResponse(PCBaseModel):
    tasks: List[TaskRunResponse]


class JobRunResponse(RecordResponse):
    run_id: str
    job_id: str
    status: JobRunStatus

    @classmethod
    def from_record(
        cls,
        record: JobRunRecord,
        tasks: Optional[List[TaskRunRecord]] = None,
        task_to_href: Optional[Callable[[TaskRunRecord], str]] = None,
    ) -> "JobRunResponse":
        links: Optional[List[Link]] = None

        if tasks:
            links = []
            if not task_to_href:
                raise ValueError("task_to_href is required if tasks are provided")

            for task in tasks:
                links.append(
                    Link(
                        rel=LinkRel.TASK,
                        href=task_to_href(task),
                        type="application/json",
                        title=f"Task: {task.task_id}",
                    )
                )

        return cls(
            run_id=record.run_id,
            job_id=record.job_id,
            status=record.status,
            links=links,
            errors=record.errors,
            created=record.created,
            updated=record.updated,
        )


class JobRunsResponse(PCBaseModel):
    jobs: List[JobRunResponse]


class WorkflowRunResponse(RecordResponse):
    dataset: str
    run_id: str
    status: WorkflowRunStatus

    workflow: Optional[WorkflowConfig] = None
    trigger_event: Optional[CloudEvent] = None
    args: Optional[Dict[str, Any]] = None

    @classmethod
    def from_record(
        cls,
        record: WorkflowRunRecord,
        jobs: Optional[List[JobRunRecord]] = None,
        job_to_href: Optional[Callable[[JobRunRecord], str]] = None,
        full: bool = True,
    ) -> "WorkflowRunResponse":
        links: Optional[List[Link]] = None

        if jobs:
            links = []
            if not job_to_href:
                raise ValueError("job_to_href is required if jobs are provided")

            for job in jobs:
                links.append(
                    Link(
                        rel=LinkRel.JOB,
                        href=job_to_href(job),
                        type="application/json",
                        title=f"Job: {job.job_id}",
                    )
                )

        workflow: Optional[WorkflowConfig] = None
        trigger_event: Optional[CloudEvent] = None
        args: Optional[Dict[str, Any]] = None

        if full:
            workflow = record.workflow
            trigger_event = record.trigger_event
            args = record.args

        return cls(
            dataset=str(record.dataset),
            run_id=record.run_id,
            status=record.status,
            links=links,
            errors=record.errors,
            created=record.created,
            updated=record.updated,
            workflow=workflow,
            trigger_event=trigger_event,
            args=args,
        )


class WorkflowRunsResponse(PCBaseModel):
    runs: List[WorkflowRunResponse]
