"""
Executes pctasks inside the dev container.
Used to mimic executing a task in Azure Batch locally.
"""

from typing import Any, Callable, Dict, List
from uuid import uuid1

from cachetools import LRUCache
from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from pctasks.cli.cli import pctasks_cmd
from pctasks.core.models.record import TaskRunStatus
from pctasks.execute.models import TaskPollResult

app = FastAPI()


def submit_task(args: List[str], callback: Callable[[TaskRunStatus], None]) -> None:
    """
    Submit a task to the local executor.
    """
    try:
        result = pctasks_cmd.main(args, standalone_mode=False)
        if result.exit_code != 0:
            callback(TaskRunStatus.FAILED)
        else:
            callback(TaskRunStatus.COMPLETED)
    except Exception:
        callback(TaskRunStatus.FAILED)


@app.post("/execute")
def execute(
    data: Dict[str, Any], request: Request, background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    id = uuid1().hex
    request.app.state._cache[id] = TaskRunStatus.PENDING

    def _update(status: TaskRunStatus) -> None:
        request.app.state._cache[id] = status

    background_tasks.add_task(submit_task, data["args"], _update)

    return {"id": id}


@app.get("/poll/{id}")
def poll(id: str, request: Request) -> Response:
    try:
        return JSONResponse(
            TaskPollResult(task_status=request.app.state._cache.get(id)).dict()
        )
    except KeyError:
        return Response(status_code=404)


@app.on_event("startup")
def startup() -> None:
    app.state._cache = LRUCache(maxsize=100)
