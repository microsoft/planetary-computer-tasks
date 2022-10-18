import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import ORJSONResponse, PlainTextResponse

from pctasks.core.cosmos.containers.records import RecordsContainer
from pctasks.core.cosmos.containers.workflow_runs import WorkflowRunsContainer
from pctasks.core.cosmos.containers.workflows import WorkflowsContainer
from pctasks.core.models.response import (
    RecordListResponse,
    WorkflowRecordListResponse,
    WorkflowRecordResponse,
    WorkflowRunRecordListResponse,
)
from pctasks.core.models.run import RunRecordType, WorkflowRunRecord
from pctasks.core.models.workflow import (
    Workflow,
    WorkflowRecord,
    WorkflowRecordType,
    WorkflowSubmitMessage,
    WorkflowSubmitRequest,
    WorkflowSubmitResult,
)
from pctasks.run.settings import RunSettings
from pctasks.run.workflow import get_workflow_runner
from pctasks.server.dependencies import PageParams
from pctasks.server.request import ParsedRequest

logger = logging.getLogger(__name__)


workflows_router = APIRouter()


@workflows_router.get(
    "/",
    summary="List workflows.",
    response_class=ORJSONResponse,
    response_model=WorkflowRecordListResponse,
)
def list_workflows(
    request: Request, page_params: PageParams = Depends(PageParams.dependency)
) -> RecordListResponse[WorkflowRecord]:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    container = RecordsContainer(WorkflowRecord)
    query = "SELECT * FROM c WHERE c.type = @type"
    pages = container.query_paged(
        query=query,
        partition_key=WorkflowRecordType.WORKFLOW,
        page_size=page_params.limit,
        continuation_token=page_params.token,
        parameters={"type": WorkflowRecordType.WORKFLOW},
    )

    return WorkflowRecordListResponse.from_pages(pages)


@workflows_router.post(
    "/{workflow_id}",
    summary="Create a workflow.",
    response_class=ORJSONResponse,
)
def create_workflow(request: Request, workflow: Workflow) -> ORJSONResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    record = WorkflowRecord(workflow_id=workflow.id, workflow=workflow)

    container = WorkflowsContainer(WorkflowRecord)
    if container.get(workflow.id, partition_key=workflow.id):
        raise HTTPException(status_code=409, detail="Workflow already exists")

    container.put(record)
    return ORJSONResponse({"workflow_id": workflow.id})


@workflows_router.put(
    "/{workflow_id}",
    summary="Update a workflow.",
    response_class=ORJSONResponse,
)
def update_workflow(request: Request, workflow: Workflow) -> ORJSONResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    record = WorkflowRecord(workflow_id=workflow.id, workflow=workflow)

    container = WorkflowsContainer(WorkflowRecord)
    if not container.get(workflow.id, partition_key=workflow.id):
        raise HTTPException(
            status_code=404, detail=f"Workflow '{workflow.id}' not found"
        )

    container.put(record)
    return ORJSONResponse({"workflow_id": workflow.id})


@workflows_router.get(
    "/{workflow_id}",
    summary="Fetch workflow.",
    response_class=ORJSONResponse,
    response_model=WorkflowRecordResponse,
)
def fetch_workflow(request: Request, workflow_id: str) -> WorkflowRecordResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    container = WorkflowsContainer(WorkflowRecord)
    record = container.get(workflow_id, partition_key=workflow_id)
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"Workflow '{workflow_id}' not found"
        )

    logger.info(record.json(indent=2))
    return WorkflowRecordResponse(record=record)


@workflows_router.post(
    "/{workflow_id}/submit",
    summary="Submit a workflow to be run.",
    response_class=ORJSONResponse,
    response_model=WorkflowSubmitResult,
)
async def submit_workflow(
    request: Request, workflow_id: str, submit_request: WorkflowSubmitRequest
) -> WorkflowSubmitResult:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    container = WorkflowsContainer(WorkflowRecord)
    workflow_record = container.get(workflow_id, partition_key=workflow_id)
    if not workflow_record:
        raise HTTPException(
            status_code=404, detail=f"Workflow '{workflow_id}' not found"
        )

    logger.info(f"Workflow: {workflow_id}")
    run_id = str(uuid4())

    submit_msg = WorkflowSubmitMessage(
        run_id=run_id,
        workflow=workflow_record.workflow,
        args=submit_request.args,
        trigger_event=submit_request.trigger_event,
    )

    workflow_runner = get_workflow_runner()

    workflow_runs = WorkflowRunsContainer(WorkflowRunRecord)
    workflow_runs.put(WorkflowRunRecord.from_submit_message(submit_msg))

    submit_result = workflow_runner.submit_workflow(submit_msg)

    return submit_result


@workflows_router.get(
    "/{run_id}/log",
    summary="Fetch log of a workflow run.",
    response_class=PlainTextResponse,
)
async def fetch_task_log(
    request: Request, run_id: str, job_id: str, partition_id: str, task_id: str
) -> PlainTextResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    workflow_runs = WorkflowRunsContainer(WorkflowRunRecord)
    record = workflow_runs.get(
        run_id,
        partition_key=run_id,
    )

    if not record:
        raise HTTPException(status_code=404, detail="Workflow run record not found")

    log_uri = record.log_uri

    if not log_uri:
        raise HTTPException(status_code=404, detail="Log URI not set on workflow run")

    run_settings = RunSettings.get()

    log_storage = run_settings.get_log_storage()
    log_path = log_storage.get_path(log_uri)
    if not log_storage.file_exists(log_path):
        raise HTTPException(status_code=404, detail="Log file not found at record URI")

    return PlainTextResponse(content=log_storage.read_text(log_path))


@workflows_router.get(
    "/{workflow_id}/runs",
    summary="List workflow runs.",
    response_class=ORJSONResponse,
    response_model=WorkflowRunRecordListResponse,
)
async def list_workflow_runs(
    request: Request,
    workflow_id: str,
    page_params: PageParams = Depends(PageParams.dependency),
) -> RecordListResponse[WorkflowRunRecord]:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    container = WorkflowsContainer(WorkflowRunRecord)
    query = "SELECT * FROM c WHERE c.workflow_id = @workflow_id AND c.type = @type"
    pages = container.query_paged(
        query=query,
        partition_key=workflow_id,
        page_size=page_params.limit,
        continuation_token=page_params.token,
        parameters={"workflow_id": workflow_id, "type": RunRecordType.WORKFLOW_RUN},
    )

    return WorkflowRunRecordListResponse.from_pages(pages)
