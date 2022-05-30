from typing import Optional

from pctasks.execute.executor.base import Executor
from pctasks.execute.executor.batch import BatchTaskExecutor
from pctasks.execute.executor.local import LocalTaskExecutor
from pctasks.execute.settings import ExecuteSettings


def get_executor(settings: Optional[ExecuteSettings] = None) -> Executor:
    settings = settings or ExecuteSettings.get()

    if settings.local_executor_url:
        return LocalTaskExecutor(settings.local_executor_url)
    else:
        return BatchTaskExecutor(settings)
