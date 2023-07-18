import contextlib
import os
from typing import Any, Optional, Tuple

import azure.identity.aio


def credential_context(
    credential: Optional[str],
) -> Tuple[Any, contextlib.AbstractAsyncContextManager]:
    """
    Get an async credential context.
    """
    if credential is None:
        credential = azure.identity.aio.DefaultAzureCredential()  # type: ignore
        credential_ctx_ = credential
    else:
        credential = {  # type: ignore
            "account_name": os.environ["FUNC_STORAGE_ACCOUNT_NAME"],
            "account_key": credential,
        }
        # async support for contextlib.nullcontext is new in 3.10
        # credential_ctx = contextlib.nullcontext

        @contextlib.asynccontextmanager
        async def nullcontext():  # type: ignore
            yield

        credential_ctx_ = nullcontext()

    assert credential_ctx_ is not None
    return credential, credential_ctx_
