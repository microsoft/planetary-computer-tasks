import logging
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import ORJSONResponse, PlainTextResponse

from pctasks.core.models.api import (
    JobRunResponse,
    JobRunsResponse,
    TaskRunResponse,
    TaskRunsResponse,
    WorkflowRunResponse,
    WorkflowRunsResponse,
)
from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.record import JobRunRecord, TaskRunRecord
from pctasks.core.utils import map_opt
from pctasks.run.settings import RunSettings
from pctasks.server.request import ParsedRequest
from pctasks.server.settings import ServerSettings

logger = logging.getLogger(__name__)


runs_router = APIRouter()


@runs_router.get(
    "/",
    summary="List workflow runs.",
    response_class=ORJSONResponse,
    response_model=WorkflowRunsResponse,
)
async def list_runs(
    request: Request,
    dataset: Optional[str] = Query(None, description="Only show runs for this dataset"),
) -> WorkflowRunsResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    tables = ServerSettings.get().record_tables
    with tables.get_workflow_run_record_table() as table:
        if dataset:
            workflows = table.get_workflow_runs(DatasetIdentifier.from_string(dataset))
        else:
            workflows = table.get_records()

    return WorkflowRunsResponse(
        runs=[
            WorkflowRunResponse.from_record(record, full=False) for record in workflows
        ]
    )


@runs_router.get(
    "/{run_id}",
    summary="Fetch workflow run.",
    response_class=ORJSONResponse,
    response_model=WorkflowRunResponse,
)
async def fetch_run(
    request: Request,
    run_id: str,
    dataset: Optional[str] = Query(None, description="Only show runs for this dataset"),
) -> WorkflowRunResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    tables = ServerSettings.get().record_tables
    with tables.get_workflow_run_record_table() as table:
        workflow = table.get_workflow_run(
            run_id=run_id,
            dataset=map_opt(lambda d: DatasetIdentifier.from_string(d), dataset),
        )

    if not workflow:
        raise HTTPException(status_code=404)

    with tables.get_job_run_record_table() as job_table:
        jobs = job_table.get_jobs(run_id=run_id)

    def _job_to_href(job: JobRunRecord) -> str:
        return os.path.join(str(request.url), "jobs", job.job_id)

    return WorkflowRunResponse.from_record(
        workflow, jobs=jobs, job_to_href=_job_to_href, full=True
    )


@runs_router.get(
    "/{run_id}/jobs",
    summary="List jobs in a workflow run.",
    response_class=ORJSONResponse,
    response_model=JobRunsResponse,
)
async def list_jobs(request: Request, run_id: str) -> JobRunsResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    tables = ServerSettings.get().record_tables
    with tables.get_job_run_record_table() as table:
        jobs = table.get_jobs(run_id=run_id)

    return JobRunsResponse(jobs=[JobRunResponse.from_record(record) for record in jobs])


@runs_router.get(
    "/{run_id}/jobs/{job_id}",
    summary="Fetch job of a workflow run.",
    response_class=ORJSONResponse,
    response_model=JobRunResponse,
)
async def fetch_job(
    request: Request,
    run_id: str,
    job_id: str,
) -> JobRunResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    tables = ServerSettings.get().record_tables
    with tables.get_job_run_record_table() as table:
        job = table.get_record(table.get_run_record_id(run_id, job_id))

    if not job:
        raise HTTPException(status_code=404)

    with tables.get_task_run_record_table() as task_table:
        tasks = task_table.get_tasks(run_id=run_id, job_id=job_id)

    def _task_to_href(task: TaskRunRecord) -> str:
        return os.path.join(str(request.url), "tasks", task.task_id)

    return JobRunResponse.from_record(job, tasks=tasks, task_to_href=_task_to_href)


@runs_router.get(
    "/{run_id}/jobs/{job_id}/tasks",
    summary="List tasks for a job in a workflow run.",
    response_class=ORJSONResponse,
    response_model=TaskRunsResponse,
)
async def list_tasks(request: Request, run_id: str, job_id: str) -> TaskRunsResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    tables = ServerSettings.get().record_tables
    with tables.get_task_run_record_table() as table:
        tasks = table.get_tasks(run_id=run_id, job_id=job_id)

    def _log_uri_to_href(task: TaskRunRecord, log_uri: str) -> str:
        return os.path.join(str(request.url), task.task_id, "logs", Path(log_uri).name)

    response_tasks: List[TaskRunResponse] = []
    for task in tasks:
        response_tasks.append(
            TaskRunResponse.from_record(task, lambda l: _log_uri_to_href(task, l))
        )

    return TaskRunsResponse(tasks=response_tasks)


@runs_router.get(
    "/{run_id}/jobs/{job_id}/tasks/{task_id}",
    summary="Fetch a task of a job of a workflow run.",
    response_class=ORJSONResponse,
    response_model=TaskRunResponse,
)
async def fetch_task(
    request: Request, run_id: str, job_id: str, task_id: str
) -> TaskRunResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    tables = ServerSettings.get().record_tables
    with tables.get_task_run_record_table() as table:
        task = table.get_record(table.get_run_record_id(run_id, job_id, task_id))

    if not task:
        raise HTTPException(status_code=404)

    def _log_uri_to_href(log_uri: str) -> str:
        return os.path.join(str(request.url), "logs", Path(log_uri).name)

    return TaskRunResponse.from_record(task, _log_uri_to_href)


@runs_router.get(
    "/{run_id}/jobs/{job_id}/tasks/{task_id}/logs/{log_name}",
    summary="Fetch logs of a task.",
    response_class=PlainTextResponse,
    response_model=TaskRunRecord,
)
async def fetch_logs(
    request: Request, run_id: str, job_id: str, task_id: str, log_name: str
) -> PlainTextResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    tables = ServerSettings.get().record_tables
    with tables.get_task_run_record_table() as table:
        task = table.get_record(table.get_run_record_id(run_id, job_id, task_id))

    if not task or not task.log_uris:
        raise HTTPException(status_code=404)

    log_uri: Optional[str] = None
    for task_log_uri in task.log_uris:
        if Path(task_log_uri).name == log_name:
            log_uri = task_log_uri
            break

    if not log_uri:
        raise HTTPException(status_code=404)

    run_settings = RunSettings.get()

    log_storage = run_settings.get_log_storage()
    log_path = log_storage.get_path(log_uri)
    if not log_storage.file_exists(log_path):
        raise HTTPException(status_code=404)

    return PlainTextResponse(content=log_storage.read_text(log_path))
