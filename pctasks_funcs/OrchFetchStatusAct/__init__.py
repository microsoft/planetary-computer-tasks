"""Terminates a running orchestration."""

import azure.durable_functions as df


async def main(id: str, starter: str) -> str:
    client = df.DurableOrchestrationClient(starter)
    status = await client.get_status(id)
    if status:
        if status.runtime_status:
            return status.runtime_status.value

    return df.OrchestrationRuntimeStatus.Completed.value
