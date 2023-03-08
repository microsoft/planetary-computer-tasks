import asyncio
import logging
import time
from typing import Awaitable, Callable

from fastapi import HTTPException, Request, Response
from starlette.responses import PlainTextResponse
from starlette.status import HTTP_504_GATEWAY_TIMEOUT

from pctasks.server.logging import get_custom_dimensions

logger = logging.getLogger(__name__)


async def handle_exceptions(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    try:
        return await call_next(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Exception when handling request",
            extra=get_custom_dimensions(request, {"stackTrace": f"{e}"}),
        )
        raise


async def timeout_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
    timeout: int,
) -> Response:
    start_time = time.time()
    try:

        return await asyncio.wait_for(call_next(request), timeout=timeout)

    except asyncio.TimeoutError:
        process_time = time.time() - start_time
        log_dimensions = get_custom_dimensions(request, {"request_time": process_time})

        logger.exception(
            "Request timeout",
            extra=log_dimensions,
        )

        ref_id = log_dimensions["custom_dimensions"].get("ref_id")
        debug_msg = f"Debug information for support: {ref_id}" if ref_id else ""

        return PlainTextResponse(
            f"The request exceeded the maximum allowed time, please try again."
            " If the issue persists, please contact planetarycomputer@microsoft.com."
            f"\n\n{debug_msg}",
            status_code=HTTP_504_GATEWAY_TIMEOUT,
        )
