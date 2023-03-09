import hashlib
import logging

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import ORJSONResponse

from pctasks.core.models.response import UploadCodeResult
from pctasks.run.settings import RunSettings
from pctasks.server.logging import log_request
from pctasks.server.request import ParsedRequest

logger = logging.getLogger(__name__)


code_router = APIRouter()


@code_router.post(
    "/upload",
    summary="Uploads a python module or package to the server for use in tasks.",
    response_class=ORJSONResponse,
    response_model=UploadCodeResult,
)
async def upload_code(request: Request, file: UploadFile) -> UploadCodeResult:
    logger.info(f"{request.headers}")
    parsed_request = ParsedRequest(request)
    log_request(parsed_request, f"Upload code: {file.filename}")

    if not parsed_request.is_authenticated:
        raise HTTPException(status_code=401, detail="Unauthorized")

    run_settings = RunSettings.get()

    code_storage = run_settings.get_code_storage()
    contents = await file.read()
    if isinstance(contents, str):
        contents = contents.encode("utf-8")

    token = hashlib.md5(contents).hexdigest()
    path = f"{token}/{file.filename}"

    code_storage.upload_bytes(contents, path)

    return UploadCodeResult(uri=code_storage.get_uri(path))
