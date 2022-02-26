import json
import logging
from typing import Optional

import azure.durable_functions as df
import azure.functions as func
from pydantic import ValidationError

from pctasks.core.logging import RunLogger
from pctasks.core.models.event import NotificationSubmitMessage
from pctasks.execute.constants import OrchestratorNames


async def main(msg: func.QueueMessage, starter: str) -> None:
    """Starts the Notify Orchestrator."""
    client = df.DurableOrchestrationClient(starter)

    event_logger: Optional[RunLogger] = None
    body = json.loads(msg.get_body().decode("utf-8"))

    try:

        message = NotificationSubmitMessage(**body)
        event_logger = RunLogger(message.processing_id)

        instance_id = await client.start_new(
            OrchestratorNames.NOTIFY, client_input=message.dict()
        )
        logging.info(f"Started orchestration with ID = '{instance_id}'.")

    except ValidationError as e:
        if event_logger:
            event_logger.log(f"Failed to parse notification message: {e}")

        raise
    except Exception as e:
        if event_logger:
            event_logger.log(f"Failed to process message: {e}")
        raise
