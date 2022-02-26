from pctasks.core.activity import wrap_activity
from pctasks.execute.constants import ActivityNames
from pctasks.execute.models import TaskSubmitMessage
from pctasks.execute.task import activities

main = wrap_activity(activities.submit, TaskSubmitMessage, ActivityNames.TASK_SUBMIT)
