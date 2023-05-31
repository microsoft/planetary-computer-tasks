"""
Cosmos DB Change Feed Dispatcher

This Azure Function dispatches updates to the `storage-events` container in
CosmosDB to the appropriate Blob Storage Queue. It's expected that PCTasks
workflows will scale in response to messages being sent to that queue.
"""
import logging
import os
import re
from typing import Optional

import azure.functions as func
import azure.identity.aio
import azure.storage.queue.aio
import pctasks_funcs_base

from pctasks.core.models.event import StorageEvent

# TODO: pre-commit-style validator for ensuring these queues exist.
# TODO: Move to prefix / suffix rules?

RULES = [
    # GOES-GLM
    (
        re.compile(
            r"https://goeseuwest\.blob\.core\.windows\.net\/noaa-goes(16|17|18)/GLM-L2-LCFA/"  # noqa: E501
        ),
        "goes-glm",
    ),
    # GOES-CMI (or at least other)
    (
        re.compile(
            r"https://goeseuwest\.blob\.core\.windows\.net\/noaa-goes(16|17|18)/"
        ),
        "goes-cmi",
    ),
    # sentinel-1-grd
    (
        re.compile(
            r"https://sentinel1euwest\.blob\.core\.windows\.net/s1-grd-stac/GRD/"
        ),
        # technically could do pre-made items queue
        "sentinel-1-grd",
    ),
    # sentinel-1-rtc
    (
        re.compile(
            r"https://sentinel1euwestrtc\.blob\.core\.windows\.net/sentinel1-grd-rtc-stac/GRD/"  # noqa: E501
        ),
        # technically could do pre-made items queue
        "sentinel-1-rtc",
    ),
    # For integration tests. It doesn't feel great putting this in here.
    (re.compile(r"http://azurite:10000/devstoreaccount1/"), "test-collection"),
]


def dispatch(url: str) -> Optional[str]:
    """
    Parameters
    ----------
    """
    # TODO: Decide whether we want 1:1 or 1:many
    for rule, queue_name in RULES:
        if rule.match(url):
            logging.info("message=matched, rule=%s, queue-name=%s", rule, queue_name)
            return queue_name
    return None


async def main(documents: func.DocumentList) -> None:
    # Types of auth to support
    # 1. Connection string (azurite)
    # 2. DefaultAzureCredential (prod)
    # TODO: local.settings.json
    account_url = os.environ["FUNC_STORAGE_QUEUE_ACCOUNT_URL"]
    credential = os.environ.get("FUNC_STORAGE_ACCOUNT_KEY", None)
    credential, credential_ctx = pctasks_funcs_base.credential_context(credential)

    async with credential_ctx:  # type: ignore
        for document in documents:
            storage_event = StorageEvent(**document)
            queue_name = dispatch(document["data"]["url"])

            if queue_name is None:
                logging.warning(
                    "No matching queue for document id=%s", storage_event.id
                )
                continue

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
