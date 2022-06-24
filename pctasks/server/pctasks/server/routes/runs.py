import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import ORJSONResponse

from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.record import JobRunRecord, TaskRunRecord, WorkflowRunRecord
from pctasks.core.utils import map_opt
from pctasks.records.settings import RecordsSettings
from pctasks.server.request import ParsedRequest

logger = logging.getLogger(__name__)


runs_router = APIRouter()


@runs_router.get(
    "/",
    summary="List workflow runs.",
    response_class=ORJSONResponse,
    response_model=List[WorkflowRunRecord],
)
async def list_runs(
    request: Request,
    dataset: Optional[str] = Query(None, description="Only show runs for this dataset"),
) -> List[WorkflowRunRecord]:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    records_settings = RecordsSettings.get()
    with records_settings.tables.get_workflow_run_record_table() as table:
        if dataset:
            workflows = table.get_workflow_runs(DatasetIdentifier.from_string(dataset))
        else:
            workflows = table.get_records()

    return workflows


@runs_router.get(
    "/{run_id}",
    summary="Fetch workflow run.",
    response_class=ORJSONResponse,
    response_model=WorkflowRunRecord,
)
async def fetch_run(
    request: Request,
    run_id: str,
    dataset: Optional[str] = Query(None, description="Only show runs for this dataset"),
) -> WorkflowRunRecord:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    records_settings = RecordsSettings.get()
    with records_settings.tables.get_workflow_run_record_table() as table:
        workflow = table.get_workflow_run(
            run_id=run_id,
            dataset=map_opt(lambda d: DatasetIdentifier.from_string(d), dataset),
        )

    if not workflow:
        raise HTTPException(status_code=404)

    return workflow


@runs_router.get(
    "/{run_id}/jobs",
    summary="List jobs in a workflow run.",
    response_class=ORJSONResponse,
    response_model=List[JobRunRecord],
)
async def list_jobs(request: Request, run_id: str) -> List[JobRunRecord]:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    records_settings = RecordsSettings.get()
    with records_settings.tables.get_job_run_record_table() as table:
        jobs = table.get_jobs(run_id=run_id)

    return jobs


@runs_router.get(
    "/{run_id}/jobs/{job_id}",
    summary="Fetch job of a workflow run.",
    response_class=ORJSONResponse,
    response_model=JobRunRecord,
)
async def fetch_job(
    request: Request,
    run_id: str,
    job_id: str,
) -> JobRunRecord:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    records_settings = RecordsSettings.get()
    with records_settings.tables.get_job_run_record_table() as table:
        job = table.get_record(table.get_run_record_id(run_id, job_id))

    if not job:
        raise HTTPException(status_code=404)

    return job


@runs_router.get(
    "/{run_id}/jobs/{job_id}/tasks",
    summary="List tasks for a job in a workflow run.",
    response_class=ORJSONResponse,
    response_model=List[TaskRunRecord],
)
async def list_tasks(request: Request, run_id: str, job_id: str) -> List[TaskRunRecord]:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    records_settings = RecordsSettings.get()
    with records_settings.tables.get_task_run_record_table() as table:
        tasks = table.get_tasks(run_id=run_id, job_id=job_id)

    return tasks


@runs_router.get(
    "/{run_id}/jobs/{job_id}/tasks/{task_id}",
    summary="Fetch job of a workflow run.",
    response_class=ORJSONResponse,
    response_model=TaskRunRecord,
)
async def fetch_task(
    request: Request, run_id: str, job_id: str, task_id: str
) -> TaskRunRecord:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    records_settings = RecordsSettings.get()
    with records_settings.tables.get_task_run_record_table() as table:
        task = table.get_record(table.get_run_record_id(run_id, job_id, task_id))

    if not task:
        raise HTTPException(status_code=404)

    return task
