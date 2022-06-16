import json
import logging
import os
from functools import lru_cache
from typing import Optional

import azure.functions as func
import requests

from pctasks.core.logging import RunLogger
from pctasks.core.models.base import RunRecordId
from pctasks.core.models.record import WorkflowRunStatus
from pctasks.core.models.workflow import WorkflowSubmitMessage

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_pctasks_server_url() -> str:
    url = os.environ.get("PCTASKS_SERVER_URL")
    if not url:
        raise Exception("PCTASKS_SERVER_URL environment variable not set")
    return url


@lru_cache(maxsize=1)
def get_pctasks_account_key() -> str:
    key = os.environ.get("PCTASKS_SERVER_ACCOUNT_KEY")
    if not key:
        raise Exception("PCTASKS_SERVER_ACCOUNT_KEY environment variable not set")
    return key


async def main(msg: func.QueueMessage, starter: str) -> None:
    logger.info(json.dumps(json.loads(starter), indent=2))

    event_logger: Optional[RunLogger] = None

    try:
        body = json.loads(msg.get_body().decode("utf-8"))
        submit_message = WorkflowSubmitMessage(**body)

        event_logger = RunLogger(
            RunRecordId(run_id=submit_message.run_id),
            logger_id="WORKFLOW",
        )

        event_logger = RunLogger(
            RunRecordId(
                run_id=submit_message.run_id,
                dataset_id=str(submit_message.workflow.get_dataset_id()),
            ),
            logger_id="WORKFLOW",
        )

        event_logger.log_event("RECEIVED")

        logger.info("***********************************")
        logger.info(f"Workflow: {submit_message.workflow.name}")
        logger.info(f"Run Id: {submit_message.run_id}")
        logger.info("***********************************")

        pctasks_server_url = get_pctasks_server_url()

        req = requests.post(
            os.path.join(pctasks_server_url, "run"),
            json=submit_message.dict(),
            headers={"Authorization": "Bearer " + get_pctasks_account_key()},
        )
        req.raise_for_status()

        logger.info(json.dumps(req.json(), indent=2))

        event_logger.log_event("SENT")

    except Exception as e:
        if event_logger:
            event_logger.log_event(
                WorkflowRunStatus.FAILED, message=f"Failed to process workflow: {e}"
            )
        logger.exception(e)
        raise
