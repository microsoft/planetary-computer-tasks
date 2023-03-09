import logging
import math
import time
from typing import Any, Dict, Optional, Union

import azure.storage.queue
import pydantic

from pctasks.core.models.base import PCBaseModel
from pctasks.core.models.task import TaskDefinition, WaitTaskResult
from pctasks.core.storage import StorageFactory
from pctasks.task.context import TaskContext
from pctasks.task.task import Task

logger = logging.getLogger(__name__)


class StreamingTaskInput(PCBaseModel):
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
    extra_env: dict, optional
        Additional environment variables to set on the pod. This is primarily
        useful for testing, setting the ``AZURITE_HOST`` for example.
    """

    queue_url: str
    queue_credential: Optional[Union[str, Dict[str, str]]] = None
    visibility_timeout: int
    min_replica_count: int = 0
    max_replica_count: int = 100
    polling_interval: int = 30
    trigger_queue_length: int = 100
    message_limit: Optional[int] = None
    extra_env: Dict[str, str] = pydantic.Field(default_factory=dict)

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
    ) -> None:
        raise NotImplementedError

    def get_extra_options(
        self, input: StreamingTaskInput, context: TaskContext
    ) -> Dict[str, Any]:
        return {}

    def run(self, input: StreamingTaskInput, context: TaskContext) -> NoOutput:
        # queue_credential should only be used for testing with azurite.
        # Otherwise, use managed identities.
        credential = input.queue_credential or azure.identity.DefaultAzureCredential()
        qc = azure.storage.queue.QueueClient.from_queue_url(
            input.queue_url, credential=credential
        )
        extra_options = self.get_extra_options(input, context)
        message_count = 0
        max_messages = input.message_limit or math.inf

        logger.info("Processing messages from queue=%s", input.queue_url)

        while message_count < max_messages:
            # mypy upgrade
            for message in qc.receive_messages(  # type: ignore
                visibility_timeout=input.visibility_timeout
            ):
                try:
                    self.process_message(
                        message=message,
                        input=input,
                        context=context,
                        **extra_options,
                    )
                except Exception:
                    logger.exception("Failed to process message")
                else:
                    # TODO: warning if we've passed the visibility timeout
                    logger.info("Processed message id=%s", message.id)
                    # mypy upgrade
                    qc.delete_message(message)  # type: ignore

                message_count += 1
                if input.message_limit and message_count >= input.message_limit:
                    logger.info("Hit limit=%d", message_count)
                    continue
            # We've drained the queue. Now we'll pause slightly before checking again.
            # TODO: some kind of exponential backoff here. From 0 - 5-10 seconds.
            n = 5
            logger.info("Sleeping for %s seconds", n)
            time.sleep(n)

        logger.info("Finishing run")
        return NoOutput()
