import json
from base64 import b64decode, b64encode

from pctasks.core.models.config import BlobConfig, TableSasConfig
from pctasks.core.models.task import TaskRunConfig, TaskRunMessage


def test_serialize_task_run_msg():
    msg = TaskRunMessage(
        args={"a": 1, "b": 2},
        config=TaskRunConfig(
            image="ingest",
            job_id="j1",
            task_id="t1",
            run_id="r1",
            task="pctasks.task.ingest.IngestTask",
            task_runs_table_config=TableSasConfig(
                table_name="t1", account_url="http://account.com", sas_token="sas"
            ),
            output_blob_config=BlobConfig(
                uri="http://account.com",
                sas_token="sas",
                account_url="http://account.com",
            ),
            log_blob_config=BlobConfig(
                uri="http://account.com",
                sas_token="sas",
                account_url="http://account.com",
            ),
        ),
    )

    msg_text = b64encode(
        msg.json(exclude_unset=True, exclude_none=True).encode("utf-8")
    ).decode("utf-8")

    msg_dict = json.loads(b64decode(msg_text.encode("utf-8")).decode("utf-8"))
    deserialized = TaskRunMessage.parse_obj(msg_dict)

    assert deserialized == msg
