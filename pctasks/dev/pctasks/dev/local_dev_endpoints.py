"""
Local dev server that:
- Executes pctask Tasks inside the dev container, mimicking
executing a task in Azure Batch locally.
- Serves out local secrets based on a secrets yaml file.
"""

import logging
import os
import time
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Dict, List
from uuid import uuid1

import yaml
from cachetools import LRUCache
from fastapi import BackgroundTasks, FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from yaml import Loader

from pctasks.cli.cli import pctasks_cmd
from pctasks.core.models.record import TaskRunStatus
from pctasks.run.models import TaskPollResult

app = FastAPI()


logger = logging.getLogger(__name__)

_task_cache_lock = Lock()
_secrets_cache_lock = Lock()

FAIL_SUBMIT_TAG = "fail_submit"
WAIT_AND_FAIL_TAG = "wait_and_fail"

DEV_SECRETS_FILE_ENV_VAR = "DEV_SECRETS_FILE"

# Execute tasks


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
    request.app.state._task_cache[id] = TaskRunStatus.PENDING

    def _update(status: TaskRunStatus) -> None:
        with _task_cache_lock:
            request.app.state._task_cache[id] = status

    tags = data.get("tags", {})
    if FAIL_SUBMIT_TAG in tags:
        _update(TaskRunStatus.FAILED)
    else:
        background_tasks.add_task(submit_task, data["args"], tags, _update)

    return {"id": id}


@app.get("/poll/{id}")
def poll(id: str, request: Request) -> Response:

    with _task_cache_lock:
        task_status = request.app.state._task_cache.get(id)
    if task_status is None:
        return Response(status_code=404)
    result = TaskPollResult(task_status=task_status)
    logger.info(f"Polling task {id}: {result.json(indent=2)}")
    return JSONResponse(result.dict())


# Serve secrets


@app.get("/secrets/{key}")
def get_secret(key: str, request: Request) -> Response:

    with _secrets_cache_lock:
        if app.state._dev_secrets_cache is None:
            secrets_path = os.getenv(DEV_SECRETS_FILE_ENV_VAR)
            if secrets_path:
                p = Path(secrets_path)
                if p.exists():
                    app.state._dev_secrets_cache = yaml.load(
                        p.read_text(), Loader=Loader
                    )
                else:
                    logger.warn(f"Dev secrest file {secrets_path} does not exist")
            if not app.state._dev_secrets_cache:
                app.state._dev_secrets_cache = {}

    value = request.app.state._dev_secrets_cache.get(key)

    logger.info(f"Fetching secret {key}. Exists: {value is not None}")
    if value:
        return PlainTextResponse(content=value)
    else:
        return Response(status_code=404)


@app.on_event("startup")
def startup() -> None:
    app.state._task_cache = LRUCache(maxsize=100)
    app.state._dev_secrets_cache = None
