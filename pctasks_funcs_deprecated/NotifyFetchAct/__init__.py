"""Fetches listeners for notification."""

from pctasks.core.activity import wrap_activity
from pctasks.execute.constants import ActivityNames
from pctasks.notify import activities
from pctasks.notify.models import NotifyFetchMessage

main = wrap_activity(
    activities.fetch_listeners, NotifyFetchMessage, ActivityNames.NOTIFY_FETCH
)
