from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional


def get_message_type_from_message(message: Dict[str, Any]) -> Optional[str]:
    return message.get("type") or message.get("eventType")


class NoMessageTypeError(Exception):
    pass


class NoHandlerFound(Exception):
    pass


class MessageHandler(ABC):
    """Base class for defining message handlers."""

    @abstractmethod
    def handle(self, message: Dict[str, Any]) -> None:
        raise NotImplementedError()


class MessageHandlers:
    def __init__(
        self, handlers: Callable[[Dict[str, Any]], Optional[MessageHandler]]
    ) -> None:
        self.handlers = handlers

    def get_handler(self, message: Dict[str, Any]) -> Optional[MessageHandler]:
        return self.handlers(message)

    def handle_message(self, message: Dict[str, Any]) -> None:
        handler = self.get_handler(message)
        if not handler:
            raise NoHandlerFound(
                f"No handler found for message type {message.get('type')}"
            )

        handler.handle(message)


class TypeMessageHandlers(MessageHandlers):
    def __init__(self, handlers: Dict[str, MessageHandler]) -> None:
        def _get_handler(message: Dict[str, Any]) -> Optional[MessageHandler]:
            message_type = get_message_type_from_message(message)
            if not message_type:
                raise NoMessageTypeError(
                    f"Could not determine message type for message: {message}"
                )
            return handlers.get(message_type)

        super().__init__(_get_handler)
