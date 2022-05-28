from typing import Optional

from pctasks.execute.executor.base import TaskExecutor
from pctasks.execute.executor.batch import BatchTaskExecutor
from pctasks.execute.executor.local import LocalTaskExecutor
from pctasks.execute.settings import ExecutorSettings


def get_executor(settings: Optional[ExecutorSettings] = None) -> TaskExecutor:
    settings = settings or ExecutorSettings.get()

    if settings.local_executor_url:
        return LocalTaskExecutor(settings.local_executor_url)
    else:
        return BatchTaskExecutor(settings)
