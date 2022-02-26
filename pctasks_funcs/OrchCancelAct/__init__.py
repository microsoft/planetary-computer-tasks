"""Terminates a running orchestration."""

import logging

import azure.durable_functions as df

logger = logging.getLogger(__name__)


async def main(id: str, starter: str) -> bool:
    client = df.DurableOrchestrationClient(starter)
    try:
        status = await client.get_status(id)
        if status.runtime_status in [
            df.OrchestrationRuntimeStatus.Running,
            df.OrchestrationRuntimeStatus.Pending,
            df.OrchestrationRuntimeStatus.ContinuedAsNew,
        ]:
            await client.terminate(id, "Cancel action.")
    except Exception as e:
        logger.exception(e)
        return False
    return True
