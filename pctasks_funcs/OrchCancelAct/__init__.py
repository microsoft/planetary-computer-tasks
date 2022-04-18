"""Terminates a running orchestration."""

import json
import logging

import azure.durable_functions as df

logger = logging.getLogger(__name__)


async def main(id: str, starter: str) -> str:
    client = df.DurableOrchestrationClient(starter)
    try:
        status = await client.get_status(id)
        if status.runtime_status in [
            df.OrchestrationRuntimeStatus.Running,
            df.OrchestrationRuntimeStatus.Pending,
            df.OrchestrationRuntimeStatus.ContinuedAsNew,
        ]:
            await client.terminate(id, "Cancel action.")
            return json.dumps(
                {"status": f"{status.runtime_status}", "terminated": True, "id": id}
            )
        else:
            return json.dumps(
                {"status": f"{status.runtime_status}", "terminated": False, "id": id}
            )
    except Exception as e:
        logger.exception(e)
        return json.dumps({"error": f"{e}", "terminated": False, "id": id})
