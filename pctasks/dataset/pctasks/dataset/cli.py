import logging
from typing import List, Optional, Tuple

import click

from pctasks.client.submit.options import opt_args
from pctasks.dataset.utils import opt_collection, opt_ds_config, opt_submit

logger = logging.getLogger(__name__)


@click.group("dataset")
@click.pass_context
def dataset_cmd(ctx: click.Context) -> None:
    """PCTasks commands for working with datasets."""
    pass


@click.command("create-chunks")
@click.argument("chunkset_id")
@opt_ds_config
@opt_collection
@opt_args
@click.option(
    "-s",
    "--since",
    help=("Only process files that have been modified at or after this datetime."),
)
@click.option("--limit", type=int, help="Limit prefix listing, used for testing")
@click.option(
    "-t",
    "--target",
    help="The target environment to process the items in.",
)
@opt_submit
@click.pass_context
def create_chunks_cmd(
    ctx: click.Context,
    chunkset_id: str,
    dataset: Optional[str] = None,
    collection: Optional[str] = None,
    arg: List[Tuple[str, str]] = [],
    since: Optional[str] = None,
    limit: Optional[int] = None,
    target: Optional[str] = None,
    submit: bool = False,
) -> None:
    """Creates workflow to generate asset chunks for bulk processing.

    Output: If -s is present, will print the run ID to stdout. Otherwise,
    will print the workflow yaml.
    """
    from . import _cli

    return _cli.create_chunks_cmd(
        ctx,
        chunkset_id,
        dataset=dataset,
        collection=collection,
        arg=arg,
        since=since,
        limit=limit,
        submit=submit,
        target=target,
    )


@click.command("process-items")
@click.argument("chunkset_id")
@opt_ds_config
@opt_collection
@opt_args
@click.option(
    "-t",
    "--target",
    help="The target environment to process the items in.",
)
@click.option("--limit", type=int, help="Limit, used for testing")
@click.option("--no-ingest", is_flag=True, help="Create ndjsons, but don't ingest.")
@click.option(
    "-e",
    "--use-existing-chunks",
    is_flag=True,
    help="Process existing chunkset, do not recreate.",
)
@click.option(
    "-s",
    "--since",
    help=("Only process files that have been modified at or after this datetime."),
)
@opt_submit
@click.pass_context
def process_items_cmd(
    ctx: click.Context,
    chunkset_id: str,
    dataset: Optional[str],
    collection: Optional[str],
    arg: List[Tuple[str, str]] = [],
    target: Optional[str] = None,
    no_ingest: bool = False,
    use_existing_chunks: bool = False,
    since: Optional[str] = None,
    limit: Optional[int] = None,
    submit: bool = False,
) -> None:
    """Generate the workflow to create and ingest items.

    Read the asset paths from the chunk file at CHUNK and
    submit a workflow to process into items and ingest into
    the database.

    Output: If -s is present, will print the run ID to stdout. Otherwise,
    will print the workflow yaml.
    """
    from . import _cli

    return _cli.process_items_cmd(
        ctx,
        chunkset_id,
        dataset,
        collection,
        arg=arg,
        target=target,
        no_ingest=no_ingest,
        use_existing_chunks=use_existing_chunks,
        since=since,
        limit=limit,
        submit=submit,
    )


@click.command("ingest-collection")
@opt_ds_config
@opt_collection
@opt_args
@click.option(
    "-t",
    "--target",
    help="The target environment to process the items in.",
)
@opt_submit
@click.pass_context
def ingest_collection_cmd(
    ctx: click.Context,
    dataset: Optional[str],
    collection: Optional[str],
    arg: List[Tuple[str, str]] = [],
    target: Optional[str] = None,
    submit: bool = False,
) -> None:
    """Generate the workflow to ingest a collection.

    This will read a collection JSON or template directory,
    specified by the "template" property of the collection
    configuration of the dataset YAML.

    Output: If -s is present, will print the run ID to stdout. Otherwise,
    will print the workflow yaml.
    """
    from . import _cli

    return _cli.ingest_collection_cmd(
        ctx, dataset, collection, arg=arg, target=target, submit=submit
    )


@click.command("list-collections")
@opt_ds_config
@opt_args
@click.pass_context
def list_collections_cmd(
    ctx: click.Context,
    dataset: Optional[str],
    arg: List[Tuple[str, str]] = [],
) -> None:
    """Lists the collection IDs contained in a dataset configuration."""
    from . import _cli

    return _cli.list_collections_cmd(ctx, dataset, arg=arg)


dataset_cmd.add_command(create_chunks_cmd)
dataset_cmd.add_command(process_items_cmd)
dataset_cmd.add_command(ingest_collection_cmd)
dataset_cmd.add_command(list_collections_cmd)
