"""
Executes pctasks inside the dev container.
Used to mimic executing a task in Azure Batch locally.
"""

import logging
import time
from typing import Any, Callable, Dict, List
from uuid import uuid1

from cachetools import LRUCache
from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.responses import JSONResponse

from pctasks.cli.cli import pctasks_cmd
from pctasks.core.models.record import TaskRunStatus
from pctasks.execute.models import TaskPollResult

app = FastAPI()


logger = logging.getLogger(__name__)


def submit_task(args: List[str], callback: Callable[[TaskRunStatus], None]) -> None:
    """
    Submit a task to the local executor.
    """
    time.sleep(1)
    try:
        pctasks_cmd.main(args)
    except SystemExit as e:
        if e.code != 0:
            logger.error(f"Task ran but returned non-zero code {e.code}")
            callback(TaskRunStatus.FAILED)
        else:
            callback(TaskRunStatus.COMPLETED)
    except Exception as e:
        logger.exception(e)
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
        result = TaskPollResult(task_status=request.app.state._cache.get(id))
        logger.info(f"Polling task {id}: {result.json(indent=2)}")
        return JSONResponse(result.dict())
    except KeyError:
        return Response(status_code=404)


@app.on_event("startup")
def startup() -> None:
    app.state._cache = LRUCache(maxsize=100)
