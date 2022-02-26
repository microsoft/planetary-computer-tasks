from typing import Any, Dict, List
from uuid import uuid4

from pctasks.core.message_handler import MessageHandler
from pctasks.core.models.event import CloudEvent
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.queues import QueueService
from pctasks.router.settings import RouterSettings


def handle_blob_event(event: CloudEvent) -> bool:
    if not event.type.startswith("Microsoft.Storage"):
        return False
    if not event.subject:
        return False

    submit_messages: List[WorkflowSubmitMessage] = []
    settings = RouterSettings.get()

    with settings.get_blob_trigger_registration_table() as table:
        registration_key = table.get_registration_key(event)
        if registration_key:
            for reg in table.get_registrations(registration_key=registration_key):
                if reg.matches(event):
                    submit_messages.append(
                        WorkflowSubmitMessage(
                            run_id=uuid4().hex,
                            workflow=reg.workflow,
                            trigger_event=event,
                        )
                    )

    if submit_messages:
        with QueueService.from_connection_string(
            connection_string=settings.queues_connection_string,
            queue_name=settings.workflow_queue_name,
        ) as queue:
            for submit_message in submit_messages:
                queue.send_message(submit_message.json().encode())

    return True


class EventGridMessageHandler(MessageHandler):
    def handle(self, message: Dict[str, Any]) -> None:
        event = CloudEvent.parse_obj(message)
        handle_blob_event(event)
