"""Sends a notification to a webhook."""

from pctasks.core.activity import wrap_activity
from pctasks.execute.constants import ActivityNames
from pctasks.notify import activities
from pctasks.notify.models import NotifyWebhookMessage

main = wrap_activity(
    activities.send_to_webhook, NotifyWebhookMessage, ActivityNames.NOTIFY_WEBHOOK
)
