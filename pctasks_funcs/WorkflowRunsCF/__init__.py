import logging
from typing import Any, Dict

import azure.functions as func

from pctasks.core.cosmos.containers.workflows import WorkflowsContainer
from pctasks.core.models.run import RunRecordType, WorkflowRunRecord

logger = logging.getLogger(__name__)


async def main(container: func.DocumentList) -> None:
    for document in container:
        data: Dict[str, Any] = document.data
        _type = data.get("type")

        if _type == RunRecordType.WORKFLOW_RUN:
            handle_workflow_run(data)
        else:
            pass


def handle_workflow_run(data: Dict[str, Any]) -> None:
    """Handle a workflow run record."""
    record = WorkflowRunRecord.parse_obj(data)

    container = WorkflowsContainer(WorkflowRunRecord)
    container.put(record)
    logger.info(f"Workflow run {record.run_id} saved to workflows container.")
