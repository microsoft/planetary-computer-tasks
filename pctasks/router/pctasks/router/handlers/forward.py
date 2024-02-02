from typing import Any, Callable, Dict

import orjson

from pctasks.core.message_handler import MessageHandler
from pctasks.core.queues import QueueService
from pctasks.router.settings import RouterSettings


class ForwardingMessageHandler(MessageHandler):
    def __init__(self, get_queue_name: Callable[[RouterSettings], str]) -> None:
        self.get_queue_name = get_queue_name

    def handle(self, message: Dict[str, Any]) -> None:
        settings = RouterSettings.get()
        with QueueService.from_connection_string(
            connection_string=settings.queues_connection_string,
            queue_name=self.get_queue_name(settings),
        ) as queue:
            queue.send_message(orjson.dumps(message, option=orjson.OPT_SERIALIZE_NUMPY))
