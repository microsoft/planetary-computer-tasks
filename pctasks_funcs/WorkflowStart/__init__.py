import json
import logging
import os
from typing import Optional

import azure.functions as func
import requests

from pctasks.core.logging import RunLogger
from pctasks.core.models.base import RunRecordId
from pctasks.core.models.record import WorkflowRunStatus
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.execute.constants import StarterNames
from pctasks.execute.models import MessageEvent
from pctasks.execute.settings import ExecuteSettings

logger = logging.getLogger(__name__)


async def main(msg: func.QueueMessage, starter: str) -> None:
    logger.info(json.dumps(json.loads(starter), indent=2))

    event_logger: Optional[RunLogger] = None

    try:
        body = json.loads(msg.get_body().decode("utf-8"))
        submit_message = WorkflowSubmitMessage(**body)

        event_logger = RunLogger(
            RunRecordId(run_id=submit_message.run_id),
            logger_id=StarterNames.WORKFLOW,
        )

        event_logger = RunLogger(
            RunRecordId(
                run_id=submit_message.run_id,
                dataset_id=str(submit_message.workflow.get_dataset_id()),
            ),
            logger_id=StarterNames.WORKFLOW,
        )

        event_logger.log_event(
            MessageEvent.MESSAGE_RECEIVED,
        )

        logger.info("***********************************")
        logger.info(f"Workflow: {submit_message.workflow.name}")
        logger.info(f"Run Id: {submit_message.run_id}")
        logger.info("***********************************")

        settings = ExecuteSettings.get()
        assert settings.pctasks_server_endpoint
        req = requests.post(
            os.path.join(settings.pctasks_server_endpoint, "run"),
            json=submit_message.dict(),
        )
        req.raise_for_status()

        logger.info(json.dumps(req.json(), indent=2))

        event_logger.log_event(
            MessageEvent.MESSAGE_SENT,
        )

    except Exception as e:
        if event_logger:
            event_logger.log_event(
                WorkflowRunStatus.FAILED, message=f"Failed to process workflow: {e}"
            )
        logger.exception(e)
        raise
