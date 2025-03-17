import logging
from typing import Any, Dict

import azure.functions as func

from pctasks.core.cosmos.containers.workflows import AsyncWorkflowsContainer
from pctasks.core.models.run import RunRecordType, WorkflowRunRecord

logger = logging.getLogger(__name__)


async def main(container: func.DocumentList) -> None:
    for document in container:
        data: Dict[str, Any] = document.data
        _type = data.get("type")

        if _type == RunRecordType.WORKFLOW_RUN:
            await handle_workflow_run(data)
        else:
            pass


async def handle_workflow_run(data: Dict[str, Any]) -> None:
    """Handle a workflow run record."""
    record = WorkflowRunRecord.model_validate(data)

    async with AsyncWorkflowsContainer(WorkflowRunRecord) as container:
        await container.put(record)

    logger.info(f"Workflow run {record.run_id} saved to workflows container.")
