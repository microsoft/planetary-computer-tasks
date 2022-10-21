from pctasks.core.constants import (
    EVENTGRID_MESSAGE_TYPE,
    NOTIFICATION_MESSAGE_TYPE,
    WORKFLOW_SUBMIT_MESSAGE_TYPE,
)
from pctasks.core.message_handler import TypeMessageHandlers
from pctasks.router.handlers.eventgrid import EventGridMessageHandler
from pctasks.router.handlers.forward import ForwardingMessageHandler

HANDLERS = TypeMessageHandlers(
    {
        EVENTGRID_MESSAGE_TYPE: EventGridMessageHandler(),
        WORKFLOW_SUBMIT_MESSAGE_TYPE: ForwardingMessageHandler(
            lambda settings: settings.workflow_queue_name
        ),
        NOTIFICATION_MESSAGE_TYPE: ForwardingMessageHandler(
            lambda settings: settings.notification_queue_name
        ),
    }
)
