import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import ORJSONResponse, PlainTextResponse

from pctasks.core.cosmos.containers.workflow_runs import (
    AsyncWorkflowRunsContainer,
    WorkflowRunsContainer,
)
from pctasks.core.models.response import (
    JobPartitionRunRecordListResponse,
    JobPartitionRunRecordResponse,
    RecordListResponse,
    RecordResponse,
    WorkflowRunRecordResponse,
)
from pctasks.core.models.run import (
    JobPartitionRunRecord,
    RunRecordType,
    WorkflowRunRecord,
)
from pctasks.run.settings import RunSettings
from pctasks.server.dependencies import PageParams, SortParams
from pctasks.server.logging import log_request
from pctasks.server.request import ParsedRequest

logger = logging.getLogger(__name__)


runs_router = APIRouter()

# TODO: Make list operations use async client after
# https://github.com/Azure/azure-sdk-for-python/issues/25104 is resolved.


@runs_router.get(
    "/{run_id}",
    summary="Fetch workflow run.",
    response_class=ORJSONResponse,
    response_model=WorkflowRunRecordResponse,
)
async def fetch_workflow_run(
    request: Request,
    run_id: str,
) -> RecordResponse[WorkflowRunRecord]:
    parsed_request = ParsedRequest(request)
    log_request(parsed_request, f"Fetch workflow run: {run_id}", run_id=run_id)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncWorkflowRunsContainer(WorkflowRunRecord) as container:
        record = await container.get(run_id, partition_key=run_id)

    if not record:
        raise HTTPException(status_code=404, detail="Not found")

    return WorkflowRunRecordResponse(record=record)


@runs_router.get(
    "/{run_id}/log",
    summary="Fetch workflow run log.",
    response_class=PlainTextResponse,
)
async def fetch_workflow_run_log(
    request: Request,
    run_id: str,
) -> PlainTextResponse:
    parsed_request = ParsedRequest(request)
    log_request(parsed_request, f"Fetch workflow run log: {run_id}", run_id=run_id)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncWorkflowRunsContainer(WorkflowRunRecord) as container:
        record = await container.get(run_id, partition_key=run_id)

    if not record:
        raise HTTPException(status_code=404, detail="Not found")

    log_uri = record.log_uri

    if not log_uri:
        raise HTTPException(status_code=404)

    run_settings = RunSettings.get()

    log_storage = run_settings.get_log_storage()
    log_path = log_storage.get_path(log_uri)
    if not log_storage.file_exists(log_path):
        raise HTTPException(status_code=404)

    return PlainTextResponse(content=log_storage.read_text(log_path))


@runs_router.get(
    "/{run_id}/jobs/{job_id}/partitions",
    summary="List job partitions.",
    response_class=ORJSONResponse,
    response_model=JobPartitionRunRecordListResponse,
)
async def list_job_partition_runs(
    request: Request,
    run_id: str,
    job_id: str,
    page_params: PageParams = Depends(PageParams.dependency),
    sort_params: SortParams = Depends(SortParams.dependency),
) -> RecordListResponse[JobPartitionRunRecord]:
    parsed_request = ParsedRequest(request)
    log_request(
        parsed_request,
        f"List job partitions: {run_id}/{job_id}",
        run_id=run_id,
        job_id=job_id,
    )

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    with WorkflowRunsContainer(JobPartitionRunRecord) as container:
        query = (
            "SELECT * FROM c WHERE c.run_id = @run_id "
            "AND c.job_id = @job_id AND c.type = @type"
        )
        query = sort_params.add_sort(query)
        pages = container.query_paged(
            query=query,
            partition_key=run_id,
            page_size=page_params.limit,
            continuation_token=page_params.token,
            parameters={
                "run_id": run_id,
                "job_id": job_id,
                "type": RunRecordType.JOB_PARTITION_RUN,
            },
        )

        return JobPartitionRunRecordListResponse.from_pages(pages)


@runs_router.get(
    "/{run_id}/jobs/{job_id}/partitions/{partition_id}",
    summary="Fetch job partition of a workflow run.",
    response_class=ORJSONResponse,
    response_model=JobPartitionRunRecordResponse,
)
async def fetch_job_partition_run(
    request: Request, run_id: str, job_id: str, partition_id: str
) -> RecordResponse[JobPartitionRunRecord]:
    parsed_request = ParsedRequest(request)
    log_request(
        parsed_request,
        f"Fetch job partition: {run_id}/{job_id}/{partition_id}",
        run_id=run_id,
        job_id=job_id,
        partition_id=partition_id,
    )

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncWorkflowRunsContainer(JobPartitionRunRecord) as container:
        record = await container.get(
            JobPartitionRunRecord.id_from(run_id, job_id, partition_id),
            partition_key=run_id,
        )

    if not record:
        raise HTTPException(status_code=404, detail="Not found")

    return RecordResponse(record=record)


@runs_router.get(
    "/{run_id}/jobs/{job_id}/partitions/{partition_id}/tasks/{task_id}/log",
    summary="Fetch los of a task.",
    response_class=PlainTextResponse,
)
async def fetch_task_log(
    request: Request, run_id: str, job_id: str, partition_id: str, task_id: str
) -> PlainTextResponse:
    parsed_request = ParsedRequest(request)
    log_request(
        parsed_request,
        f"Fetch task log: {run_id}/{job_id}/{partition_id}/{task_id}",
        run_id=run_id,
        job_id=job_id,
        partition_id=partition_id,
        task_id=task_id,
    )

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncWorkflowRunsContainer(JobPartitionRunRecord) as container:
        record = await container.get(
            JobPartitionRunRecord.id_from(run_id, job_id, partition_id),
            partition_key=run_id,
        )

    if not record:
        raise HTTPException(status_code=404, detail="Job partition record not found")

    tasks = {t.task_id: t for t in record.tasks}
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")

    log_uri = task.log_uri

    if not log_uri:
        raise HTTPException(status_code=404, detail="Log URI not set on task run")

    run_settings = RunSettings.get()

    log_storage = run_settings.get_log_storage()
    log_path = log_storage.get_path(log_uri)
    if not log_storage.file_exists(log_path):
        raise HTTPException(status_code=404, detail="File does not exist at log URI")

    return PlainTextResponse(content=log_storage.read_text(log_path))
