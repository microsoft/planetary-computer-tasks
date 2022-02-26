"""Sends a notification to event grid channels."""

from pctasks.core.activity import wrap_activity
from pctasks.execute.constants import ActivityNames
from pctasks.notify import activities
from pctasks.notify.models import NotifyEventGridChannelMessage

main = wrap_activity(
    activities.send_to_eventgrid, NotifyEventGridChannelMessage, ActivityNames.NOTIFY_EG
)
