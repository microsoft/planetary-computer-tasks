"""Fetches listeners for notification."""

from pctasks.core.activity import wrap_activity
from pctasks.notify import activities
from pctasks.notify.models import NotifyFetchMessage
from pctasks.run.constants import ActivityNames

main = wrap_activity(
    activities.fetch_listeners, NotifyFetchMessage, ActivityNames.NOTIFY_FETCH
)
