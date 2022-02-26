from typing import Optional

from pctasks.execute.executor.base import Executor
from pctasks.execute.executor.batch import BatchExecutor
from pctasks.execute.executor.local import LocalExecutor
from pctasks.execute.settings import ExecutorSettings


def get_executor(settings: Optional[ExecutorSettings] = None) -> Executor:
    settings = settings or ExecutorSettings.get()

    if settings.local_executor_url:
        return LocalExecutor(settings.local_executor_url)
    else:
        return BatchExecutor()
