"""Sends a notification to a webhook."""

from pctasks.core.activity import wrap_activity
from pctasks.notify import activities
from pctasks.notify.models import NotifyWebhookMessage
from pctasks.run.constants import ActivityNames

main = wrap_activity(
    activities.send_to_webhook, NotifyWebhookMessage, ActivityNames.NOTIFY_WEBHOOK
)
