from pctasks.core.activity import wrap_activity
from pctasks.core.logging import RunLogger
from pctasks.core.models.activity import ActivityMessage
from pctasks.core.models.base import PCBaseModel, RunRecordId


def test_activity_serializes_properly() -> None:
    class TestModel(PCBaseModel):
        input: str
        output: str

    def process_model(m: TestModel, event_logger: RunLogger) -> TestModel:
        return TestModel(input=f"{m.input}-processed", output=f"{m.output}-processed")

    wrapped = wrap_activity(process_model, TestModel, "test_activity")

    result_str: str = wrapped(
        ActivityMessage(
            msg=TestModel(input="test-in", output="test-out"),
            run_record_id=RunRecordId(
                job_id="job-id", task_id="task-id", run_id="run-id"
            ),
        ).json()
    )

    result = TestModel.model_validate_json(result_str)

    assert result.input == "test-in-processed"
    assert result.output == "test-out-processed"
