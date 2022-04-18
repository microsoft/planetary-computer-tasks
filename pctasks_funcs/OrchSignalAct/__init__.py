"""Sends a signal to an orchestrator."""

import logging

import azure.durable_functions as df

from func_lib.models import OrchSignal

logger = logging.getLogger(__name__)


async def main(msg: str, starter: str) -> str:
    client = df.DurableOrchestrationClient(starter)

    orch_signal = OrchSignal.parse_raw(msg)

    await client.raise_event(
        instance_id=orch_signal.instance_id,
        event_name=orch_signal.event_name,
        event_data=orch_signal.event_data or {},
    )

    return f"Raised signal {orch_signal.event_name} to {orch_signal.instance_id}"
