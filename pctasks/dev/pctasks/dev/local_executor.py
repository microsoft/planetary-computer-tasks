"""
Executes pctasks inside the dev container.
Used to mimic executing a task in Azure Batch locally.
"""

import logging
import time
from threading import Lock
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

cache_lock = Lock()

FAIL_SUBMIT_TAG = "fail_submit"
WAIT_AND_FAIL_TAG = "wait_and_fail"


def submit_task(
    args: List[str], tags: Dict[str, str], callback: Callable[[TaskRunStatus], None]
) -> None:
    """
    Submit a task to the local executor.
    """
    if WAIT_AND_FAIL_TAG in tags:
        sleep_seconds = WAIT_AND_FAIL_TAG
        callback(TaskRunStatus.RUNNING)
        time.sleep(int(sleep_seconds))
        callback(TaskRunStatus.FAILED)
    else:
        callback(TaskRunStatus.RUNNING)
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
        with cache_lock:
            request.app.state._cache[id] = status

    tags = data.get("tags", {})
    if FAIL_SUBMIT_TAG in tags:
        _update(TaskRunStatus.FAILED)
    else:
        background_tasks.add_task(submit_task, data["args"], tags, _update)

    return {"id": id}


@app.get("/poll/{id}")
def poll(id: str, request: Request) -> Response:
    try:
        with cache_lock:
            result = TaskPollResult(task_status=request.app.state._cache.get(id))
        logger.info(f"Polling task {id}: {result.json(indent=2)}")
        return JSONResponse(result.dict())
    except KeyError:
        return Response(status_code=404)


@app.on_event("startup")
def startup() -> None:
    app.state._cache = LRUCache(maxsize=100)
