from __future__ import annotations

import contextlib
import json
import logging
import os

import azure.functions as func
import azure.identity
import azure.storage.queue.aio


async def main(documents: func.DocumentList) -> None:

    account_url = os.environ["FUNC_STORAGE_QUEUE_ACCOUNT_URL"]
    credential = os.environ.get("FUNC_STORAGE_ACCOUNT_KEY", None)

    if credential is None:
        credential = azure.identity.aio.DefaultAzureCredential()  # type: ignore
        credential_ctx = credential
    else:
        credential = {  # type: ignore
            "account_name": os.environ["FUNC_STORAGE_ACCOUNT_NAME"],
            "account_key": credential,
        }
        # async support for contextlib.nullcontext is new in 3.10
        # credential_ctx = contextlib.nullcontext

        @contextlib.asynccontextmanager
        async def credential_ctx_():  # type: ignore
            yield

        credential_ctx = credential_ctx_()

    queue_name = "ingest"
    logging.info("Sending messages to %s/%s", account_url, queue_name)

    async with credential_ctx:  # type: ignore
        # TODO: figure out what we want for queue-url.
        qc = azure.storage.queue.aio.QueueClient(
            account_url,
            queue_name,
            credential=credential,
        )
        async with qc:
            for document in documents:
                if document["type"] == "StacItem":
                    logging.info("Processing document %s", document["id"])
                    message = transform_document(document)
                    await qc.send_message(message)
                    logging.info("Processed document %s", document["id"])


def transform_document(document: func.Document) -> str:
    item = document["item"]
    return json.dumps(item)
