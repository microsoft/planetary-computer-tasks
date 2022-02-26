"""Polls the executor for task status."""

from pctasks.core.activity import wrap_activity
from pctasks.execute.constants import ActivityNames
from pctasks.execute.models import TaskPollMessage
from pctasks.execute.task import activities

main = wrap_activity(activities.poll, TaskPollMessage, ActivityNames.TASK_POLL)
