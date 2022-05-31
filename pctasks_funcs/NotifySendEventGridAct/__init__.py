"""Sends a notification to event grid channels."""

from pctasks.core.activity import wrap_activity
from pctasks.notify import activities
from pctasks.notify.models import NotifyEventGridChannelMessage
from pctasks.run.constants import ActivityNames

main = wrap_activity(
    activities.send_to_eventgrid, NotifyEventGridChannelMessage, ActivityNames.NOTIFY_EG
)
