from __future__ import annotations

import json
import logging
import os

import azure.functions as func
import azure.identity
import azure.storage.queue.aio
import pctasks_funcs_base


async def main(documents: func.DocumentList) -> None:

    account_url = os.environ["FUNC_STORAGE_QUEUE_ACCOUNT_URL"]
    credential = os.environ.get("FUNC_STORAGE_ACCOUNT_KEY", None)
    credential_ctx = pctasks_funcs_base.credential_context()

    queue_name = "ingest"
    logging.info("Sending messages to %s/%s", account_url, queue_name)

    filtered_documents = [
        document for document in documents if document["type"] == "StacItem"
    ]

    if filtered_documents:
        async with credential_ctx:  # type: ignore
            qc = azure.storage.queue.aio.QueueClient(
                account_url,
                queue_name,
                credential=credential,
            )
            async with qc:
                for document in filtered_documents:
                    if document["type"] == "StacItem":
                        logging.info("Processing document %s", document["id"])
                        message = transform_document(document)
                        await qc.send_message(message)
                        logging.info("Processed document %s", document["id"])


def transform_document(document: func.Document) -> str:
    item = document["item"]
    return json.dumps(item)
