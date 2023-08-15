"""
Cosmos DB Change Feed Dispatcher

This Azure Function dispatches updates to the `storage-events` container in
CosmosDB to the appropriate Blob Storage Queue. It's expected that PCTasks
workflows will scale in response to messages being sent to that queue.

## Dispatch Configuration

Storage events are dispatched based on the `document.data.url` of the
Cloud Event, which is a URL like

    https://goeseuwest.blob.core.windows.net/noaa-goes16/GLM-L2-LCFA/...

We rely on a naming convention for environment variables to determine which
storage queues to dispatch to. The pattern is

    PCTASKS_DISPATCH__<QUEUE_NAME>__QUEUE_NAME
    PCTASKS_DISPATCH__<QUEUE_NAME>__PREFIX
    PCTASKS_DISPATCH__<QUEUE_NAME>__<SUFFIX>

For example, the rule

    PCTASKS_DISPATCH__GOES_GLM__QUEUE_NAME=goes-glm
    PCTASKS_DISPATCH__GOES_GLM__PREFIX=https://goeseuwest.blob.core.windows.net/noaa-goes16/GLM-L2-LCFA/

maps to the nested object:

    {
        "PCTASKS_DISPATCH": {
            "GOES_GLM": {
                "QUEUE_NAME": "goes-glm",
                "PREFIX": "https://goeseuwest.blob.core.windows.net/noaa-goes16/GLM-L2-LCFA/"  # noqa: E501
            }
        }
    }


And would ensure that a cloud event with the URL given above would be dispatched
to the `goes-glm` queue.
"""
import json
import logging
import os

import azure.functions as func
import azure.identity.aio
import azure.storage.queue.aio
import pctasks_funcs_base

from pctasks.core.models.event import StorageEvent


def load_dispatch_config() -> list[tuple[str, str | None, str | None]]:
    config = []
    for k, v in os.environ.items():
        if k.startswith("PCTASKS_DISPATCH__"):
            _, queue_name, key = k.split("__")
            if key == "QUEUE_NAME":
                prefix = os.environ.get(f"PCTASKS_DISPATCH__{queue_name}__PREFIX", None)
                suffix = os.environ.get(f"PCTASKS_DISPATCH__{queue_name}__SUFFIX", None)
                config.append((v, prefix, suffix))

    return config


def dispatch(url: str, rules: list[tuple[str, str | None, str | None]]) -> list[str]:
    """
    Parameters
    ----------
    """
    queues = []
    for queue_name, prefix, suffix in rules:
        matches_prefix = (prefix is None) or url.startswith(prefix)
        matches_suffix = (suffix is None) or url.endswith(suffix)

        if matches_prefix and matches_suffix:
            queues.append(queue_name)

    # We deduplicate here. Ideally, we wouldn't have duplicates in the first place.
    queues = list(set(queues))

    return queues


async def main(documents: func.DocumentList) -> None:
    # Types of auth to support
    # 1. Connection string (azurite)
    # 2. DefaultAzureCredential (prod)
    # TODO: local.settings.json
    account_url = os.environ["FUNC_STORAGE_QUEUE_ACCOUNT_URL"]
    credential = os.environ.get("FUNC_STORAGE_ACCOUNT_KEY", None)
    credential, credential_ctx = pctasks_funcs_base.credential_context(credential)

    config = load_dispatch_config()

    async with credential_ctx:  # type: ignore
        for document in documents:
            storage_event = StorageEvent(**document)
            queues = dispatch(storage_event.data.url, config)

            if not queues:
                log_message = {
                    "message": "Dropped message",
                    "type": "storage-event-dispatch",
                    "matched": False,
                    "url": storage_event.data.url,
                    "id": storage_event.id,
                }

                logging.warning(json.dumps(log_message))
                continue

            for queue_name in queues:
                queue_client = azure.storage.queue.aio.QueueClient(
                    account_url, queue_name=queue_name, credential=credential
                )
                log_message = {
                    "message": "Dispatched message",
                    "type": "storage-event-dispatch",
                    "matched": True,
                    "url": storage_event.data.url,
                    "id": storage_event.id,
                    "queue_url": (
                        f"{queue_client.primary_hostname}/{queue_client.queue_name}"
                    ),
                }

                logging.info(json.dumps(log_message))
                async with queue_client:
                    await queue_client.send_message(storage_event.json())
