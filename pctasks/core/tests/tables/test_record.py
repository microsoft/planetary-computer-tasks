from pctasks.core.models.dataset import DatasetIdentifier
from pctasks.core.models.record import WorkflowRunRecord
from pctasks.core.models.workflow import WorkflowConfig, WorkflowRunStatus
from pctasks.core.tables.base import decode_dict, encode_model


def test_encode_created():
    workflow = """
    name: Test workflow
    dataset: microsoft/test-dataset

    args:
      - name

    jobs:
      test-job:
        tasks:
          - id: test-task
            image_key: ingest-prod
            task: tests.test_submit.MockTask
            args:
              hello: ${{ args.name }}
    """
    workflow = WorkflowConfig.from_yaml(workflow)
    ds = DatasetIdentifier(name="test-dataset", owner="microsoft")
    wr = WorkflowRunRecord(
        status=WorkflowRunStatus.SUBMITTED,
        workflow=workflow,
        dataset=ds,
        run_id="test-run",
    )

    assert wr.created is not None

    encoded = encode_model(wr)
    decoded = decode_dict(encoded)

    assert "created" in decoded
    assert decoded["created"] == wr.created.isoformat()
