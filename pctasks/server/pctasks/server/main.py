import logging
import os
from typing import Any, Awaitable, Callable, Dict

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse

from pctasks.server.logging import init_logging
from pctasks.server.middleware import handle_exceptions, timeout_middleware
from pctasks.server.routes import code, runs, workflows
from pctasks.server.settings import ServerSettings

# Initialize logging
init_logging("tasks")

settings = ServerSettings.get()

DEBUG: bool = os.getenv("DEBUG") == "TRUE" or False

logger = logging.getLogger(__name__)

# Get the root path if set in the environment
APP_ROOT_PATH = os.environ.get("APP_ROOT_PATH", "")
logger.info(f"APP_ROOT_PATH: {APP_ROOT_PATH}")

app = FastAPI(root_path=APP_ROOT_PATH, default_response_class=ORJSONResponse)


app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def _handle_exceptions(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    return await handle_exceptions(request, call_next)


@app.middleware("http")
async def _timeout_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Add a timeout to all requests."""
    return await timeout_middleware(
        request, call_next, timeout=settings.request_timeout
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> PlainTextResponse:
    return PlainTextResponse(str(exc), status_code=400)


@app.get("/_mgmt/ping")
async def ping() -> Dict[str, Any]:
    """Liveliness/readiness probe."""
    return {"message": "PONG"}


app.include_router(
    workflows.workflows_router,
    prefix="/workflows",
    tags=["Workflows"],
)

app.include_router(
    code.code_router,
    prefix="/code",
    tags=["Manage code"],
)

app.include_router(
    runs.runs_router,
    prefix="/runs",
    tags=["Fetch workflow run information"],
)
