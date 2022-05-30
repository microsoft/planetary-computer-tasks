"""Polls the executor for task status."""

from pctasks.core.activity import wrap_activity
from pctasks.execute.constants import ActivityNames
from pctasks.execute.models import HandleTaskResultMessage
from pctasks.execute.task import activities


def event_tag(msg: HandleTaskResultMessage) -> str:
    return f"{msg.task_result_type} {msg.run_record_id}"


main = wrap_activity(
    activities.handle_result,
    HandleTaskResultMessage,
    ActivityNames.TASK_HANDLE_RESULT,
    event_tag=event_tag,
)
