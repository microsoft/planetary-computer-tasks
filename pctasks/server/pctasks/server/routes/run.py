import logging
from typing import Any, Dict, Union

from fastapi import APIRouter, Request
from fastapi.responses import Response

from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.run.argo.client import ArgoClient
from pctasks.run.settings import RunSettings
from pctasks.server.settings import ServerSettings

logger = logging.getLogger(__name__)


run_router = APIRouter()


@run_router.post(
    "",
    summary="Run a workflow.",
)
async def run_workflow(
    request: Request, workflow: WorkflowSubmitMessage
) -> Union[Dict[str, Any], Response]:
    logger.info(f"Workflow: {workflow.workflow.name}")

    server_settings = ServerSettings.get()

    if (
        request.headers.get("Authorization")
        != "Bearer " + server_settings.server_account_key
    ):
        return Response(status_code=401, content="Unauthorized")

    run_settings = RunSettings.get()
    argo_host = run_settings.argo_host
    argo_token = run_settings.argo_token

    # Settings validated on startup
    assert argo_host
    assert argo_token

    argo_client = ArgoClient(
        host=argo_host, token=argo_token, namespace=run_settings.argo_namespace
    )

    argo_result = argo_client.submit_workflow(
        workflow, run_settings=run_settings, runner_image=server_settings.runner_image
    )

    return {"run_id": workflow.run_id, "argo": argo_result.get("metadata")}
