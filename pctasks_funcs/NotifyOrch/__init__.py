import logging
from typing import Any, Optional

import azure.durable_functions as df

from pctasks.core.models.event import NotificationSubmitMessage
from pctasks.notify.models import (
    NotifyEventGridChannelMessage,
    NotifyFetchMessage,
    NotifyFetchResult,
    NotifyWebhookMessage,
)
from pctasks.run.constants import ActivityNames

logger = logging.getLogger(__name__)


def orchestrator(context: df.DurableOrchestrationContext) -> Any:
    note_message_str: Optional[str] = context.get_input()
    if not note_message_str:
        raise Exception("No message received")

    message = NotificationSubmitMessage.parse_obj(note_message_str)

    fetch_msg = NotifyFetchMessage(
        notification=message.notification, target_environment=message.target_environment
    )
    fetch_result_dict = yield context.call_activity(
        ActivityNames.NOTIFY_FETCH, input_=fetch_msg.dict()
    )
    fetch_result = NotifyFetchResult.parse_obj(fetch_result_dict)

    notify_actions = []
    for registration in fetch_result.registrations:
        if registration.webhook_endpoint:
            notify_actions.append(
                context.call_activity(
                    ActivityNames.NOTIFY_WEBHOOK,
                    input_=NotifyWebhookMessage(
                        endpoint=registration.webhook_endpoint,
                        event=message.notification.event,
                    ).dict(),
                )
            )
        if registration.eventgrid_channel_info:

            notify_actions.append(
                context.call_activity(
                    ActivityNames.NOTIFY_EG,
                    input_=NotifyEventGridChannelMessage(
                        channel_info=registration.eventgrid_channel_info,
                        event=message.notification.event,
                    ).dict(),
                )
            )

    yield context.task_all(notify_actions)


main = df.Orchestrator.create(orchestrator)
