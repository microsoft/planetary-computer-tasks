import json

import azure.functions as func

from pctasks.router.message_handler import HANDLERS


def main(msg: func.QueueMessage) -> None:
    body = json.loads(msg.get_body().decode("utf-8"))
    HANDLERS.handle_message(body)
