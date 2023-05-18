import pytest

from pctasks.core.models.event import (
    StorageEvent,
    StorageEventRecord,
    StorageEventType,
    CreateItemErrorRecord,
)


@pytest.fixture
def event_body():
    body = {
        "source": "/subscriptions/{subscription-id}/resourceGroups/Storage/providers/Microsoft.Storage/storageAccounts/my-storage-account",  # noqa: E501
        "subject": "/blobServices/default/containers/my-file-system/blobs/new-file.txt",
        "type": "Microsoft.Storage.BlobCreated",
        "time": "2017-06-26T18:41:00.9584103Z",
        "id": "831e1650-001e-001b-66ab-eeb76e069631",
        "data": {
            "api": "CreateFile",
            "clientRequestId": "6d79dbfb-0e37-4fc4-981f-442c9ca65760",
            "requestId": "831e1650-001e-001b-66ab-eeb76e000000",
            "eTag": '"0x8D4BCC2E4835CD0"',
            "contentType": "text/plain",
            "contentLength": 0,
            "contentOffset": 0,
            "blobType": "BlockBlob",
            "url": "https://my-storage-account.dfs.core.windows.net/my-file-system/new-file.txt",  # noqa: E501
            "sequencer": "00000000000004420000000000028963",
            "storageDiagnostics": {"batchId": "b68529f3-68cd-4744-baa4-3c0498ec19f0"},
        },
        "specversion": "1.0",
    }
    return body


def test_storage_event_created(event_body):
    event = StorageEvent.parse_obj(event_body)
    assert event.time == "2017-06-26T18:41:00.9584103Z"
    assert event.type == StorageEventType.CREATED
    assert event.data.api == "CreateFile"
    assert (
        event.data.url
        == "https://my-storage-account.dfs.core.windows.net/my-file-system/new-file.txt"
    )  # noqa: E501


def test_storage_events_record(event_body):
    record = StorageEventRecord.parse_obj(event_body)

    assert record.get_id() == "831e1650-001e-001b-66ab-eeb76e069631"
    assert StorageEventRecord.migrate(event_body)


def test_create_item_error(event_body):
    event_body["run_id"] = "test"
    event_body["traceback"] = "ZeroDivisionError"
    event_body["dequeue_count"] = 1
    record = CreateItemErrorRecord.parse_obj(event_body)

    assert record.get_id() == "831e1650-001e-001b-66ab-eeb76e069631:test:1"
