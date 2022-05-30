import logging
from typing import Any, Dict
from fastapi import APIRouter, Request
from pctasks.core.models.workflow import WorkflowSubmitMessage

logger = logging.getLogger(__name__)


run_router = APIRouter()


@run_router.post(
    "",
    summary="Run a workflow.",
)
async def run_workflow(
    request: Request, workflow: WorkflowSubmitMessage
) -> Dict[str, Any]:
    logger.info(f"Workflow: {workflow.workflow.name}")

    return {"run_id": workflow.run_id}
