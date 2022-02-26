from typing import List, Optional

import click
from strictyaml.exceptions import MarkedYAMLError

from pctasks.cli.cli import PCTasksCommandContext
from pctasks.core.yaml import YamlValidationError
from pctasks.dataset.chunks.chunkset import (
    ALL_CHUNK_PREFIX,
    ASSET_CHUNKS_PREFIX,
    ITEM_CHUNKS_PREFIX,
)
from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
from pctasks.dataset.items.messages import ProcessItemsWorkflow
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.utils import opt_collection, opt_dry_run, opt_ds_config
from pctasks.submit.client import SubmitClient
from pctasks.submit.settings import SubmitSettings


@click.command("process-items")
@click.argument("chunkset_id")
@opt_ds_config
@opt_collection
@click.option("--local", is_flag=True, help="Run locally, do not submit as a task")
@click.option("--limit", type=int, help="Limit, used for testing")
@opt_dry_run
@click.pass_context
def process_items_cmd(
    ctx: click.Context,
    chunkset_id: str,
    dataset: Optional[str] = None,
    collection: Optional[str] = None,
    local: bool = False,
    limit: Optional[int] = None,
    dry_run: bool = False,
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

    workflows: List[ProcessItemsWorkflow] = []

    for chunk_path in chunk_storage.list_files():
        ndjson_path = (
            f"{chunkset_id}/{ITEM_CHUNKS_PREFIX}/{ALL_CHUNK_PREFIX}/{chunk_path}"
        )

        workflows.append(
            ProcessItemsWorkflow.create(
                collection_id=collection_config.id,
                image=ds_config.image,
                collection_class=collection_config.collection_class,
                asset_chunk_uri=chunk_storage.get_uri(chunk_path),
                item_chunk_uri=item_storage.get_uri(ndjson_path),
                limit=limit,
            )
        )

    for workflow in workflows:
        settings = SubmitSettings.get(context.profile, context.settings_file)
        SubmitClient(settings).submit_workflow(workflow)
