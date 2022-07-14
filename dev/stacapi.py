# Taken from https://github.com/stac-utils/stac-fastapi/blob/2.3.0/stac_fastapi/pgstac/stac_fastapi/pgstac/app.py
"""FastAPI application using PGStac."""
"""FastAPI application using PGStac."""
import os

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from starlette.middleware.cors import CORSMiddleware

from stac_fastapi.api.app import StacApi
from stac_fastapi.api.models import create_get_request_model, create_post_request_model
from stac_fastapi.extensions.core import (
    ContextExtension,
    FieldsExtension,
    SortExtension,
    TokenPaginationExtension,
    TransactionExtension,
)
from stac_fastapi.pgstac.config import Settings
from stac_fastapi.pgstac.core import CoreCrudClient
from stac_fastapi.pgstac.db import close_db_connection, connect_to_db
from stac_fastapi.pgstac.extensions import QueryExtension
from stac_fastapi.pgstac.transactions import TransactionsClient
from stac_fastapi.pgstac.types.search import PgstacSearch

settings = Settings()
extensions = [
    TransactionExtension(
        client=TransactionsClient(),
        settings=settings,
        response_class=ORJSONResponse,
    ),
    QueryExtension(),
    SortExtension(),
    FieldsExtension(),
    TokenPaginationExtension(),
    ContextExtension(),
]

post_request_model = create_post_request_model(extensions, base_model=PgstacSearch)

APP_ROOT_PATH = os.environ.get("APP_ROOT_PATH", "")
print(f"APP_ROOT_PATH: {APP_ROOT_PATH}")

api = StacApi(
    title="PCTasks development STAC",
    description="STAC catalog for PCTasks development environment",
    settings=settings,
    extensions=extensions,
    client=CoreCrudClient(post_request_model=post_request_model),
    response_class=ORJSONResponse,
    app=FastAPI(root_path=APP_ROOT_PATH, default_response_class=ORJSONResponse),
    search_get_request_model=create_get_request_model(extensions),
    search_post_request_model=post_request_model,
)
app = api.app

app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Connect to database on startup."""
    await connect_to_db(app)


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection."""
    await close_db_connection(app)


def run():
    """Run app from command line using uvicorn if available."""
    try:
        import uvicorn

        uvicorn.run(
            "stac_fastapi.pgstac.app:app",
            host=settings.app_host,
            port=settings.app_port,
            log_level="info",
            reload=settings.reload,
        )
    except ImportError:
        raise RuntimeError("Uvicorn must be installed in order to use command")


if __name__ == "__main__":
    run()
