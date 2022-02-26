import logging
from typing import List, Optional
from uuid import uuid4

import click
from pystac.utils import str_to_datetime
from strictyaml.exceptions import MarkedYAMLError

from pctasks.cli.cli import PCTasksCommandContext
from pctasks.core.models.workflow import WorkflowSubmitMessage
from pctasks.core.utils import map_opt
from pctasks.core.yaml import YamlValidationError
from pctasks.dataset.chunks.chunkset import ALL_CHUNK_PREFIX, ASSET_CHUNKS_PREFIX
from pctasks.dataset.chunks.models import CreateChunksWorkflowConfig
from pctasks.dataset.chunks.task import CreateChunksInput, CreateChunksTask
from pctasks.dataset.constants import DEFAULT_DATASET_YAML_PATH
from pctasks.dataset.template import template_dataset_file
from pctasks.dataset.utils import opt_collection, opt_dry_run, opt_ds_config
from pctasks.submit.client import SubmitClient
from pctasks.submit.settings import SubmitSettings

logger = logging.getLogger(__name__)


@click.command("create-chunks")
@click.argument("chunkset_id")
@opt_ds_config
@opt_collection
@click.option(
    "-s",
    "--since",
    help=("Only process files that have been modified at or after this datetime."),
)
@click.option("--local", is_flag=True, help="Run locally, do not submit as a task")
@click.option("--limit", type=int, help="Limit prefix linking, used for testing")
@opt_dry_run
@click.pass_context
def create_chunks_cmd(
    ctx: click.Context,
    chunkset_id: str,
    dataset: Optional[str] = None,
    collection: Optional[str] = None,
    since: Optional[str] = None,
    local: bool = False,
    limit: Optional[int] = None,
    dry_run: bool = False,
) -> None:
    """Creates a chunkset for bulk processing."""
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
    chunk_storage_config = collection_config.chunk_storage

    chunk_folder = f"{chunkset_id}/{ASSET_CHUNKS_PREFIX}/{ALL_CHUNK_PREFIX}"

    create_chunks_args: List[CreateChunksInput] = []

    for asset_storage_config in collection_config.asset_storage:
        chunks_config = asset_storage_config.chunks
        assets_uri = asset_storage_config.get_uri()
        logger.debug(f"Processing {assets_uri}...")
        if asset_storage_config.chunks.splits:
            logger.debug(f"{len(asset_storage_config.chunks.splits)} splits found.")
            splits = asset_storage_config.chunks.splits
            asset_storage = asset_storage_config.get_storage()

            click.echo(click.style(f"Walking prefixes in {assets_uri}...", fg="green"))
            prefixes: List[str] = []
            split_prefixes = [
                s.prefix + "/" if s.prefix and not s.prefix.endswith("/") else s.prefix
                for s in splits
            ]
            for split_config in splits:
                split_prefix = split_config.prefix
                split_prefixes = split_prefixes[1:]

                for root, folders, _ in asset_storage.walk(
                    max_depth=split_config.depth,
                    min_depth=split_config.depth,
                    name_starts_with=split_prefix,
                    walk_limit=limit,
                    file_limit=limit,
                ):
                    print(".", end="", flush=True)
                    # Avoid walking through the same prefix twice
                    if split_prefixes:
                        for other_prefix in split_prefixes:
                            if other_prefix in folders:
                                folders.remove(other_prefix)

                    prefixes.append(f"{root}/")

            print()

            for prefix in prefixes:
                prefix_chunk_folder = f"{chunk_folder}/{prefix}"
                create_chunks_args.append(
                    CreateChunksInput(
                        src_storage_uri=assets_uri,
                        dst_storage_uri=chunk_storage_config.get_uri(
                            prefix_chunk_folder
                        ),
                        chunk_length=chunks_config.length,
                        since=map_opt(str_to_datetime, since),
                    )
                )

        else:
            create_chunks_args.append(
                CreateChunksInput(
                    src_storage_uri=assets_uri,
                    dst_storage_uri=chunk_storage_config.get_uri(chunk_folder),
                    chunk_length=chunks_config.length,
                    since=map_opt(str_to_datetime, since),
                )
            )

    group_id = uuid4().hex

    def get_submit_message(args: CreateChunksInput) -> WorkflowSubmitMessage:
        return WorkflowSubmitMessage(
            workflow=CreateChunksWorkflowConfig.create(
                dataset=ds_config.get_identifier(),
                group_id=group_id,
                collection_id=collection_config.id,
                image=ds_config.image,
                tokens=collection_config.get_tokens(),
                args=args,
            )
        )

    if dry_run:
        click.echo(
            click.style(
                f"Would create {len(create_chunks_args)} chunks. "
                "Workflow for first chunk:",
                fg="yellow",
            )
        )
        if local:
            print(create_chunks_args[0].to_yaml())
        else:
            msg = get_submit_message(create_chunks_args[0])
            print(msg.to_yaml())

    else:
        if local:
            for args in create_chunks_args:
                CreateChunksTask.create_chunks(args)
        else:
            settings = SubmitSettings.get(context.profile, context.settings_file)
            with SubmitClient(settings) as client:
                for args in create_chunks_args:
                    msg = get_submit_message(args)
                    click.echo(click.style(f"  Submitting {msg.run_id}...", fg="green"))
                    client.submit_workflow(msg)
