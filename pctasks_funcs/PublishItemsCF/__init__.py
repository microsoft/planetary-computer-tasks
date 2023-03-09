from __future__ import annotations

import json
import logging

import azure.identity
import azure.functions as func
import azure.storage.queue


def main(documents: func.DocumentList) -> str:
    credential = azure.identity.DefaultAzureCredential()
    qc = azure.storage.queue.QueueClient(
        "https://pclowlatency.queue.core.windows.net/",
        "ingest-test",
        credential=credential,
    )
    # azurite credentials
    
    for document in documents:
        logging.info("Processing document id=%s", document["id"])
        message = transform_document(document)
        qc.send_message(message)


def transform_document(document: func.Document) -> str:
    item = document["data"]["item"]
    return json.dumps(item)