import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import ORJSONResponse

from pctasks.core.cosmos.containers.records import AsyncRecordsContainer
from pctasks.core.cosmos.containers.workflow_runs import AsyncWorkflowRunsContainer
from pctasks.core.cosmos.containers.workflows import AsyncWorkflowsContainer
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
    WorkflowRunStatus,
    WorkflowSubmitMessage,
    WorkflowSubmitRequest,
    WorkflowSubmitResult,
)
from pctasks.run.workflow import get_workflow_runner
from pctasks.server.dependencies import PageParams, SortParams
from pctasks.server.request import ParsedRequest

logger = logging.getLogger(__name__)


workflows_router = APIRouter()


@workflows_router.get(
    "/",
    summary="List workflows.",
    response_class=ORJSONResponse,
    response_model=WorkflowRecordListResponse,
)
async def list_workflows(
    request: Request,
    page_params: PageParams = Depends(PageParams.dependency),
    sort_params: SortParams = Depends(SortParams.dependency),
) -> RecordListResponse[WorkflowRecord]:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncRecordsContainer(WorkflowRecord) as container:
        query = "SELECT * FROM c WHERE c.type = @type"
        query = sort_params.add_sort(query)
        pages = container.query_paged(
            query=query,
            partition_key=WorkflowRecordType.WORKFLOW,
            page_size=page_params.limit,
            continuation_token=page_params.token,
            parameters={"type": WorkflowRecordType.WORKFLOW},
        )

        return WorkflowRecordListResponse.from_pages([p async for p in pages])


@workflows_router.post(
    "/{workflow_id}",
    summary="Create a workflow.",
    response_class=ORJSONResponse,
)
async def create_workflow(request: Request, workflow: Workflow) -> ORJSONResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    record = WorkflowRecord(workflow_id=workflow.id, workflow=workflow)

    async with AsyncWorkflowsContainer(WorkflowRecord) as container:
        existing = await container.get(workflow.id, partition_key=workflow.id)
        if existing:
            raise HTTPException(status_code=409, detail="Workflow already exists")

        await container.put(record)

    return ORJSONResponse({"workflow_id": workflow.id})


@workflows_router.put(
    "/{workflow_id}",
    summary="Update a workflow.",
    response_class=ORJSONResponse,
)
async def update_workflow(request: Request, workflow: Workflow) -> ORJSONResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    record = WorkflowRecord(workflow_id=workflow.id, workflow=workflow)

    async with AsyncWorkflowsContainer(WorkflowRecord) as container:
        existing = await container.get(workflow.id, partition_key=workflow.id)
        if not existing:
            raise HTTPException(
                status_code=404, detail=f"Workflow '{workflow.id}' not found"
            )

        await container.put(record)

    return ORJSONResponse({"workflow_id": workflow.id})


@workflows_router.get(
    "/{workflow_id}",
    summary="Fetch workflow.",
    response_class=ORJSONResponse,
    response_model=WorkflowRecordResponse,
)
async def fetch_workflow(request: Request, workflow_id: str) -> WorkflowRecordResponse:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncWorkflowsContainer(WorkflowRecord) as container:
        record = await container.get(workflow_id, partition_key=workflow_id)

    if record is None:
        raise HTTPException(
            status_code=404, detail=f"Workflow '{workflow_id}' not found"
        )

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

    async with AsyncWorkflowsContainer(WorkflowRecord) as container:
        workflow_record = await container.get(workflow_id, partition_key=workflow_id)
        if not workflow_record:
            raise HTTPException(
                status_code=404, detail=f"Workflow '{workflow_id}' not found"
            )

    logger.info(f"Submitting workflow: {workflow_id}")
    run_id = str(uuid4())

    submit_msg = WorkflowSubmitMessage(
        run_id=run_id,
        workflow=workflow_record.workflow,
        args=submit_request.args,
        trigger_event=submit_request.trigger_event,
    )

    workflow_runner = get_workflow_runner()

    async with AsyncWorkflowRunsContainer(WorkflowRunRecord) as workflow_runs:
        await workflow_runs.put(WorkflowRunRecord.from_submit_message(submit_msg))

        try:
            submit_result = workflow_runner.submit_workflow(submit_msg)
            return submit_result
        except Exception as e:
            logger.exception(e)
            r = await workflow_runs.get(run_id, partition_key=run_id)
            if r:
                r.set_status(WorkflowRunStatus.FAILED)
                await workflow_runs.put(r)
            raise


@workflows_router.get(
    "/{workflow_id}/runs",
    summary="List workflow runs.",
    response_class=ORJSONResponse,
    response_model=WorkflowRunRecordListResponse,
)
async def list_workflow_runs(
    request: Request,
    workflow_id: str,
    sort_params: SortParams = Depends(SortParams.dependency),
    page_params: PageParams = Depends(PageParams.dependency),
) -> RecordListResponse[WorkflowRunRecord]:
    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    async with AsyncWorkflowsContainer(WorkflowRunRecord) as container:
        query = "SELECT * FROM c WHERE c.workflow_id = @workflow_id AND c.type = @type"
        query = sort_params.add_sort(query)
        pages = container.query_paged(
            query=query,
            partition_key=workflow_id,
            page_size=page_params.limit,
            continuation_token=page_params.token,
            parameters={"workflow_id": workflow_id, "type": RunRecordType.WORKFLOW_RUN},
        )

        return WorkflowRunRecordListResponse.from_pages([p async for p in pages])
