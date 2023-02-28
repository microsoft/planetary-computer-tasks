import json
from pathlib import Path
from typing import List, Optional

import click

from pctasks.client.workflow.commands import cli_handle_workflow
from pctasks.core.constants import DEFAULT_TARGET_ENVIRONMENT
from pctasks.core.context import PCTasksCommandContext
from pctasks.core.models.workflow import JobDefinition, WorkflowDefinition
from pctasks.ingest.models import IngestNdjsonInput, IngestTaskConfig, NdjsonFolder
from pctasks.ingest.settings import IngestOptions, IngestSettings
from pctasks.ingest.utils import generate_collection_json


def ingest_ndjson_cmd(
    ctx: click.Context,
    collection_id: str,
    ndjson_folder_uri: str,
    target: str,
    insert_group_size: int,
    insert_only: bool,
    num_workers: Optional[int],
    work_mem: Optional[int],
    extension: List[str],
    name_starts_with: Optional[str],
    ends_with: Optional[str],
    matches: Optional[str],
    owner: str,
    submit: bool,
    limit: Optional[int],
    workflow_id: Optional[str] = None,
    add_service_principal: bool = True,
) -> None:
    """Ingest Items from a folder of Ndjsons.

    Ingest NDJson files from the folder at NDJSON_FOLDER_URI containing items for
    collection COLLECTION_ID into target environment TARGET.

    This command will print the workflow to stdout, and submit it if the --submit
    flag is provided. If submitted, stdout will contain the run ID for the workflow.
    """
    context: PCTasksCommandContext = ctx.obj
    ingest_settings = IngestSettings.get(context.profile, context.settings_file)

    image_key = ingest_settings.image_keys.get_key(target)

    ingest_config = IngestOptions(
        insert_group_size=insert_group_size,
        insert_only=insert_only,
        num_workers=num_workers,
        work_mem=work_mem,
    )

    task = IngestTaskConfig.from_ndjson(
        ndjson_data=IngestNdjsonInput(
            ndjson_folder=NdjsonFolder(
                uri=ndjson_folder_uri,
                name_starts_with=name_starts_with,
                extensions=extension,
                ends_with=ends_with,
                matches=matches,
                limit=limit,
            )
        ),
        target=target,
        option=ingest_config,
        add_service_principal=add_service_principal,
    )

    job = JobDefinition(tasks=[task])

    workflow = WorkflowDefinition(
        name=f"Ingest NDJsons from {ndjson_folder_uri}",
        dataset=f"{owner}/{collection_id}",
        collection_id=collection_id,
        image_key=image_key,
        target_environment=target,
        jobs={
            "ingest-items": job,
        },
    )

    cli_handle_workflow(ctx, workflow_def=workflow, args=None, workflow_id=workflow_id)


def ingest_collection_cmd(
    ctx: click.Context,
    path: str,
    target: Optional[str],
    owner: str,
    submit: bool,
) -> None:
    """Ingest collection at PATH.

    If PATH is a directory, will read collection template information
    from the directory. Otherwise PATH must bea complete STAC Collection JSON.
    """
    collection_path = Path(path)

    target = target or DEFAULT_TARGET_ENVIRONMENT

    if collection_path.is_dir():
        collection = generate_collection_json(collection_path)
    else:
        with open(collection_path, "r") as f:
            collection = json.load(f)

    collection_id = collection.get("id")
    if not collection_id:
        raise click.UsageError(f"Collection must have an id: {path}")

    task = IngestTaskConfig.from_collection(collection=collection, target=target)

    workflow = WorkflowDefinition(
        name=f"Ingest Collection: {collection_id}",
        dataset=f"{owner}/{collection_id}",
        target_environment=target,
        jobs={
            "ingest-collection": JobDefinition(tasks=[task]),
        },
    )

    cli_handle_workflow(ctx, workflow_def=workflow, args=None)
