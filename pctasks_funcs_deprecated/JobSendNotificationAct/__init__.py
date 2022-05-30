from pctasks.core.activity import wrap_activity
from pctasks.core.models.event import NotificationSubmitMessage
from pctasks.execute.constants import ActivityNames
from pctasks.execute.task import activities

main = wrap_activity(
    activities.send_notification,
    NotificationSubmitMessage,
    ActivityNames.JOB_SEND_NOTIFICATION,
)
