import logging
from typing import Any, Callable, Generator

import azure.durable_functions as df
from azure.durable_functions.models.Task import TaskBase

logger = logging.getLogger(__name__)


# TODO
class TypedOrchestrator:
    def __init__(
        self,
        orechestrator: Callable[
            [df.DurableOrchestrationContext], Generator[TaskBase, Any, Any]
        ],
    ):
        self.orechestrator = orechestrator

    def df_orechestrator(
        self, context: df.DurableOrchestrationContext
    ) -> Generator[TaskBase, Any, Any]:
        gen = self.orechestrator(context)
        try:
            while True:
                logger.warn("\n\nGETTING NEXT\n\n")
                task = next(gen)
                logger.warn("\n\nBEGIN  YEIDL NEXT\n\n")
                result = yield task
                logger.warn("\n\nEND YIELD  BEGIN SEND\n\n")
                gen.send(result)
                logger.warn("\n\nEND SEND\n\n")
        except StopIteration as e:
            return e.value
