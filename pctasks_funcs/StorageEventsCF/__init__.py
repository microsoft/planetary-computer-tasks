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
                "PREFIX": "https://goeseuwest.blob.core.windows.net/noaa-goes16/GLM-L2-LCFA/"
            }
        }
    }
    

And would ensure that a cloud event with the URL given above would be dispatched
to the `goes-glm` queue.
"""
import logging
import os

# import re
from typing import Optional

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
                print("Load", queue_name, v, prefix, suffix)
                config.append((v, prefix, suffix))

    return config


def dispatch(url: str, rules: list[tuple[str, str | None, str | None]]) -> list[str]:
    """
    Parameters
    ----------
    """
    # TODO: Decide whether we want 1:1 or 1:many
    queues = []
    for queue_name, prefix, suffix in rules:
        matches_prefix = (prefix is None) or (url.startswith(prefix))
        matches_suffix = (suffix is None) or (url.endswith(suffix))

        if matches_prefix and matches_suffix:
            logging.info(
                "message=matched, queue-name=%s, prefix=%s, suffix=%s",
                queue_name,
                prefix,
                suffix,
            )
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

            if queues is None:
                logging.warning(
                    "No matching queue for document id=%s", storage_event.id
                )
                continue

            for queue_name in queues:
                queue_client = azure.storage.queue.aio.QueueClient(
                    account_url, queue_name=queue_name, credential=credential
                )
                logging.info(
                    "message=dispatching document, id=%s, queue_url=%s",
                    storage_event.id,
                    f"{queue_client.primary_hostname}/{queue_client.queue_name}",
                )
                async with queue_client:
                    await queue_client.send_message(storage_event.json())
