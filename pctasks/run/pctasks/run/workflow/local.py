from concurrent import futures
from threading import Lock
from typing import Optional

from pctasks.core.models.record import WorkflowRunStatus
from pctasks.core.models.workflow import WorkflowSubmitMessage, WorkflowSubmitResult
from pctasks.run.workflow.base import WorkflowRunner
from pctasks.run.workflow.executor.remote import RemoteWorkflowExecutor

_pool_lock = Lock()
_workflow_count = 0
_thread_pool: Optional[futures.ThreadPoolExecutor] = None


def _shutdown_pool() -> None:
    global _thread_pool
    global _workflow_count
    with _pool_lock:
        _workflow_count -= 1
        if _thread_pool and _workflow_count == 0:
            _thread_pool.shutdown()
            _thread_pool = None


class LocalWorkflowRunner(WorkflowRunner):
    """Executes a workflow in the local process on a background thread."""

    def submit_workflow(self, workflow: WorkflowSubmitMessage) -> WorkflowSubmitResult:
        global _workflow_count
        global _thread_pool
        executor = RemoteWorkflowExecutor(self.settings)
        with _pool_lock:
            if _thread_pool is None:
                _thread_pool = futures.ThreadPoolExecutor(max_workers=1)
            _thread_pool.submit(executor.execute_workflow, workflow).add_done_callback(
                lambda _: _shutdown_pool()
            )

        return WorkflowSubmitResult(
            dataset=workflow.workflow.get_dataset_id(),
            run_id=workflow.run_id,
            status=WorkflowRunStatus.RUNNING,
        )
