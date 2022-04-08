from typing import List, Optional, Tuple

import click
from strictyaml.exceptions import MarkedYAMLError

from pctasks.cli.cli import PCTasksCommandContext, cli_output, cli_print
from pctasks.core.models.base import ForeachConfig
from pctasks.core.models.workflow import (
    JobConfig,
    WorkflowConfig,
    WorkflowSubmitMessage,
)
from pctasks.core.yaml import YamlValidationError
from pctasks.dataset.chunks.constants import (
    ALL_CHUNK_PREFIX,
    ASSET_CHUNKS_PREFIX,
    ITEM_CHUNKS_PREFIX,
)
from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
from pctasks.dataset.items.models import CreateItemsTaskConfig
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.utils import opt_collection, opt_ds_config, opt_submit
from pctasks.ingest.models import IngestNdjsonInput, IngestTaskConfig
from pctasks.submit.client import SubmitClient
from pctasks.submit.settings import SubmitSettings


@click.command("process-items")
@click.argument("chunkset_id")
@opt_ds_config
@opt_collection
@click.option(
    "-t",
    "--target",
    help="The target environment to process the items in.",
)
@click.option("--limit", type=int, help="Limit, used for testing")
@opt_submit
@click.pass_context
def process_items_cmd(
    ctx: click.Context,
    chunkset_id: str,
    dataset: Optional[str],
    collection: Optional[str],
    target: str,
    limit: Optional[int] = None,
    submit: bool = False,
) -> None:
    """Create and ingest items.

    Read the asset paths from the chunk file at CHUNK and
    submit a workflow to process into items and ingest into
    the database.
    """
    context: PCTasksCommandContext = ctx.obj
    try:
        ds_config = template_dataset_file(dataset)
    except (MarkedYAMLError, YamlValidationError) as e:
        raise click.ClickException(f"Invalid dataset config.\n{e}")
    except FileNotFoundError:
        raise click.ClickException(
            "No dataset config found. Use --config to specify "
            f"or name your config {DEFAULT_DATASET_YAML_PATH}."
        )
    if not ds_config:
        raise click.ClickException("No dataset config found.")

    collection_config = ds_config.get_collection(collection)

    chunk_folder = f"{chunkset_id}/{ASSET_CHUNKS_PREFIX}/{ALL_CHUNK_PREFIX}"
    chunk_storage_config = collection_config.chunk_storage
    chunk_storage = chunk_storage_config.get_storage().get_substorage(chunk_folder)

    item_storage_config = collection_config.item_storage
    item_storage = item_storage_config.get_storage()

    chunk_uris: List[Tuple[str, str]] = []

    for chunk_path in chunk_storage.list_files():
        ndjson_path = (
            f"{chunkset_id}/{ITEM_CHUNKS_PREFIX}/{ALL_CHUNK_PREFIX}/{chunk_path}"
        )

        asset_chunk_uri = chunk_storage.get_uri(chunk_path)
        item_chunk_uri = item_storage.get_uri(ndjson_path)

        chunk_uris.append((asset_chunk_uri, item_chunk_uri))

    create_items_task = CreateItemsTaskConfig.from_collection(
        ds_config,
        collection_config,
        limit=limit,
        asset_chunk_uri="${{ item[0] }}",
        item_chunk_uri="${{ item[1] }}",
    )

    ingest_items_task = IngestTaskConfig.from_ndjson(
        ndjson_data=IngestNdjsonInput(
            uris="${{" + f"tasks.{create_items_task.id}.output.ndjson_uri " + " }}",
        ),
        target=target,
    )

    process_items_job: JobConfig = JobConfig(
        tasks=[create_items_task, ingest_items_task],
        foreach=ForeachConfig(items=chunk_uris),
    )

    workflow = WorkflowConfig(
        name=f"Process items for {collection_config.id} - {chunkset_id}",
        dataset=ds_config.get_identifier(),
        collection_id=collection_config.id,
        image=ds_config.image,
        tokens=collection_config.get_tokens(),
        jobs={
            "process-items": process_items_job,
        },
    )

    submit_message = WorkflowSubmitMessage(workflow=workflow)

    if not submit:
        cli_output(submit_message.to_yaml())
    else:
        settings = SubmitSettings.get(context.profile, context.settings_file)
        with SubmitClient(settings) as client:
            cli_print(
                click.style(f"  Submitting {submit_message.run_id}...", fg="green")
            )
            client.submit_workflow(submit_message)
