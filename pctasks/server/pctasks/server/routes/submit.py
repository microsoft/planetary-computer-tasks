import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import ORJSONResponse

from pctasks.core.models.workflow import WorkflowSubmitMessage, WorkflowSubmitResult
from pctasks.run.settings import RunSettings
from pctasks.run.workflow import get_workflow_runner
from pctasks.server.request import ParsedRequest

logger = logging.getLogger(__name__)


submit_router = APIRouter()


@submit_router.post(
    "/",
    summary="Submit a workflow.",
    response_class=ORJSONResponse,
    response_model=WorkflowSubmitResult,
)
async def submit_workflow(
    request: Request, workflow: WorkflowSubmitMessage
) -> WorkflowSubmitResult:
    logger.info(f"Workflow: {workflow.workflow.name}")

    parsed_request = ParsedRequest(request)

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    workflow_runner = get_workflow_runner(RunSettings.get())

    return workflow_runner.submit_workflow(
        workflow,
    )
