import datetime
import logging
import math
import time
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union

import azure.identity
import azure.storage.queue

from pctasks.core.models.base import PCBaseModel
from pctasks.task.context import TaskContext

logger = logging.getLogger(__name__)


class StreamingTaskInput(Protocol):
    streaming_options: "StreamingTaskOptions"


class StreamingTaskOptions(PCBaseModel):
    """
    Base class for all streaming task inputs.

    This class defines the required configuration for a streaming task.

    Parameters
    ----------
    queue_url: str
        The full URL to the queue this task is processing. This will typically
        be like ``https://<account-name>.queue.core.windows.net/<queue-name>``
    queue_credential: string or dictionary, optional.
        This can be used to authentication with the storage queue. By default,
        you should rely on managed identities and DefaultAzureCredential.
        For testing with azurite, you can provide a dictionary with
        ``account_name`` and ``account_key``.
    visibility_timeout: int
        The number of seconds to before the queue service assumes processing
        fails and makes the message visible again. This should be some multiple
        of the typical processing time.
    min_replica_count, max_replica_count: int
        The minimum and maximum number of concurrent workers that should process
        items from this queue.
    polling_interval: int, default 30
        How often KEDA should poll the queue to check for new messages and rescale.
    trigger_queue_length: int, default 100
        Controls the scaling factor.
    message_limit: Optional[int]
        The maximum number of messages from the queue to process. Once reached,
        the processing function will exit. If not set, the function will run
        forever, relying on some external system (like KEDA) to stop processing.

        This is primarily useful for testing.
    """

    queue_url: str
    queue_credential: Optional[Union[str, Dict[str, str]]] = None
    visibility_timeout: int
    min_replica_count: int = 0
    max_replica_count: int = 100
    polling_interval: int = 30
    trigger_queue_length: int = 100
    message_limit: Optional[int] = None

    class Config:
        extra = "forbid"


class NoOutput(PCBaseModel):
    # just for the type checker
    pass


class StreamingTaskMixin:
    def process_message(
        self,
        message: azure.storage.queue.QueueMessage,
        input: StreamingTaskInput,
        context: TaskContext,
        **extra_options: Dict[str, Any],
    ) -> Tuple[List[Any], List[Any]]:
        """
        Process messages from the the queue.

        Subclasses must implement this method. They should return a tuple of
        two lists. The first is the list of OK results, and the second is the
        list of errors.

        Pair this with the ``finalize_method`` to persist these records.
        """
        raise NotImplementedError

    def finalize_message(
        self, ok: List[Any], errors: List[Any], extra_options: Dict[str, Any]
    ) -> None:
        """
        Finalize the results from ``process_message``.
        """
        raise NotImplementedError

    def get_extra_options(
        self, input: StreamingTaskInput, context: TaskContext
    ) -> Dict[str, Any]:
        return {}

    def cleanup(self, extra_options: Dict[str, Any]) -> None:
        """Method that will always be called as streaming run exits."""
        pass

    def run(self, input: StreamingTaskInput, context: TaskContext) -> NoOutput:
        # queue_credential should only be used for testing with azurite.
        # Otherwise, use managed identities.
        credential = (
            input.streaming_options.queue_credential
            or azure.identity.DefaultAzureCredential()
        )
        qc = azure.storage.queue.QueueClient.from_queue_url(
            input.streaming_options.queue_url, credential=credential
        )
        extra_options = self.get_extra_options(input, context)
        message_count = 0
        max_messages = input.streaming_options.message_limit or math.inf

        logger.info(
            "Processing messages from queue=%s", input.streaming_options.queue_url
        )

        try:
            while message_count < max_messages:
                # mypy upgrade
                for message in qc.receive_messages(  # type: ignore
                    visibility_timeout=input.streaming_options.visibility_timeout
                ):
                    try:
                        ok, errors = self.process_message(
                            message=message,
                            input=input,
                            context=context,
                            **extra_options,
                        )
                        self.finalize_message(ok, errors, extra_options)
                    except Exception:
                        # TODO: Clean up the logging on failures. We log here and in
                        # dataset.streaming:process_message
                        # TODO: Implement a dead letter queue
                        logger.exception("Failed to process message")
                        if message.dequeue_count >= 3:
                            logger.info(
                                "Deleting message after 3 failures. id=%s", message.id
                            )
                            qc.delete_message(message)  # type: ignore

                    else:
                        logger.info("Processed message id=%s", message.id)
                        time_to_visible = (
                            message.next_visible_on
                            - datetime.datetime.now(tz=datetime.timezone.utc)
                        )

                        if time_to_visible < datetime.timedelta(0):
                            logger.warning(
                                "Deleting message that is already visible. Consider "
                                "setting a higher visibility timeout. message_id=%s",
                                message.id,
                            )
                        qc.delete_message(message)  # type: ignore

                    message_count += 1
                    if (
                        input.streaming_options.message_limit
                        and message_count >= input.streaming_options.message_limit
                    ):
                        logger.info("Hit limit=%d", message_count)
                        continue
                # We've drained the queue.
                # Now we'll pause slightly before checking again.
                # TODO: some kind of exponential backoff here. From 0 - 5-10 seconds.
                n = 5
                logger.info("Sleeping for %s seconds", n)
                time.sleep(n)
        finally:
            self.cleanup(extra_options)

        logger.info("Finishing run")
        return NoOutput()
