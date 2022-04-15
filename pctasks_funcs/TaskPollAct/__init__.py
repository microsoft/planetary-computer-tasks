"""Polls the executor for task status."""

import json
from pctasks.core.activity import wrap_activity
from pctasks.execute.constants import ActivityNames
from pctasks.execute.models import TaskPollMessage
from pctasks.execute.task import activities


def event_tag(msg: TaskPollMessage) -> str:
    return json.dumps(msg.executor_id)


main = wrap_activity(
    activities.poll, TaskPollMessage, ActivityNames.TASK_POLL, event_tag=event_tag
)
