import json
import logging

import azure.functions as func

from pctasks.operations.message_handler import HANDLERS

logger = logging.getLogger(__name__)


async def main(msg: func.QueueMessage) -> None:
    HANDLERS.handle_message(json.loads(msg.get_body().decode("utf-8")))
