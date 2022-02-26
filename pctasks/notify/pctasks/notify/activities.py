from typing import List
from urllib import request

from pctasks.core.logging import RunLogger
from pctasks.core.models.registration import STACItemEventRegistration
from pctasks.notify.models import (
    NotifyEventGridChannelMessage,
    NotifyFetchMessage,
    NotifyFetchResult,
    NotifyResult,
    NotifyWebhookMessage,
)
from pctasks.notify.settings import NotificationSettings


def fetch_listeners(
    msg: NotifyFetchMessage, event_logger: RunLogger
) -> NotifyFetchResult:
    settings = NotificationSettings.get()

    registrations: List[STACItemEventRegistration] = []
    with settings.get_webhook_registration_table() as table:
        registration_key = table.get_registration_key(
            msg.notification, msg.target_environment
        )
        if registration_key:
            for registration in table.get_registrations(registration_key):
                if registration.matches(msg.notification.event):
                    registrations.append(registration)

    return NotifyFetchResult(registrations=registrations)


def send_to_webhook(msg: NotifyWebhookMessage, event_logger: RunLogger) -> NotifyResult:
    try:
        req = request.Request(msg.endpoint, data=msg.event.json().encode("utf-8"))
        resp = request.urlopen(req)
        return NotifyResult(success=resp.status == 200)
    except Exception:
        event_logger.log(f"Notify failed to send to webhook: {msg.endpoint}")
        return NotifyResult(success=False)


def send_to_eventgrid(
    msg: NotifyEventGridChannelMessage, event_logger: RunLogger
) -> NotifyResult:
    # TODO
    try:
        event_logger.log(f"TODO: send to eventgrid: {msg.channel_info}")
        return NotifyResult()
    except Exception:
        event_logger.log("Notify failed to send to eventgrid!")
        return NotifyResult(success=False)
