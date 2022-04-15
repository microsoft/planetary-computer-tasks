from pctasks.core.activity import wrap_activity
from pctasks.execute.constants import ActivityNames
from pctasks.execute.models import TaskSubmitMessage
from pctasks.execute.task import activities


def event_tag(msg: TaskSubmitMessage) -> str:
    return str(msg.get_run_record_id())


main = wrap_activity(
    activities.submit, TaskSubmitMessage, ActivityNames.TASK_SUBMIT, event_tag=event_tag
)
