"""FastAPI application using PGStac."""
import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, StarletteHTTPException
from fastapi.responses import ORJSONResponse
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import PlainTextResponse

from pctasks.server.routes import run


DEBUG: bool = os.getenv("DEBUG") == "TRUE" or False

logger = logging.getLogger(__name__)

# Get the root path if set in the environment
APP_ROOT_PATH = os.environ.get("APP_ROOT_PATH", "")
logger.info(f"APP_ROOT_PATH: {APP_ROOT_PATH}")

app = FastAPI(root_path=APP_ROOT_PATH, default_response_class=ORJSONResponse)


app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request, exc: HTTPException
) -> PlainTextResponse:
    return PlainTextResponse(
        str(exc.detail), status_code=exc.status_code, headers=exc.headers
    )


@app.exception_handler(StarletteHTTPException)
async def base_http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> PlainTextResponse:
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> PlainTextResponse:
    return PlainTextResponse(str(exc), status_code=400)


@app.get("/_mgmt/ping")
async def ping():
    """Liveliness/readiness probe."""
    return {"message": "PONG"}


app.include_router(
    run.run_router,
    prefix="/run",
    tags=["Run workflows"],
)
