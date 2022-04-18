import json
import logging

import azure.durable_functions as df
import azure.functions as func

from pctasks.core.models.task import TaskRunSignalMessage
from pctasks.execute.constants import EventNames

logger = logging.getLogger(__name__)


async def main(msg: func.QueueMessage, starter: str) -> None:
    signal_msg = TaskRunSignalMessage.parse_obj(
        json.loads(msg.get_body().decode("utf-8"))
    )
    instance_id = signal_msg.signal_target_id
    client = df.DurableOrchestrationClient(starter)
    status = await client.get_status(instance_id)
    if status.runtime_status == df.OrchestrationRuntimeStatus.Running:
        logger.info(f"Sending signal to {signal_msg.signal_target_id}...")
        await client.raise_event(
            instance_id=signal_msg.signal_target_id,
            event_name=EventNames.TASK_SIGNAL,
            event_data=signal_msg.data.dict(),
        )
    else:
        logger.warning(f"Orchestration {instance_id} is not running.")
