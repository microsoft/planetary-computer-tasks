import logging
from typing import List, Optional, Tuple

import click

from pctasks.client.workflow.options import opt_args
from pctasks.dataset.utils import (
    opt_collection,
    opt_confirm,
    opt_ds_config,
    opt_submit,
    opt_upsert,
    opt_workflow_id,
)

logger = logging.getLogger(__name__)


@click.group("dataset")
@click.pass_context
def dataset_cmd(ctx: click.Context) -> None:
    """PCTasks commands for working with datasets."""
    pass

@click.command("create-splits")
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
@opt_confirm
@opt_upsert
@opt_workflow_id
@click.pass_context
def create_splits_cmd(
    ctx: click.Context,
    dataset: Optional[str] = None,
    collection: Optional[str] = None,
    arg: List[Tuple[str, str]] = [],
    since: Optional[str] = None,
    limit: Optional[int] = None,
    target: Optional[str] = None,
    submit: bool = False,
    confirm: bool = False,
    upsert: bool = False,
    workflow_id: Optional[str] = None,
) -> None:
    """Creates workflow to generate asset chunks for bulk processing.

    Use -u or --upsert to upsert the workflow through the API.
    Use -s or --submit to upsert and submit the workflow through the API.

    Output: If neither -u or -s is present, Will print the workflow yaml.
    If -u is present, will print the workflow ID to stdout.
    If -s is present, will print the run ID to stdout.
    """
    from . import _cli

    return _cli.create_splits_cmd(
        ctx,
        dataset=dataset,
        collection=collection,
        arg=arg,
        limit=limit,
        submit=submit,
        upsert=upsert,
        target=target,
        workflow_id=workflow_id,
        auto_confirm=confirm,
    )



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
@opt_confirm
@opt_upsert
@opt_workflow_id
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
    confirm: bool = False,
    upsert: bool = False,
    workflow_id: Optional[str] = None,
) -> None:
    """Creates workflow to generate asset chunks for bulk processing.

    Use -u or --upsert to upsert the workflow through the API.
    Use -s or --submit to upsert and submit the workflow through the API.

    Output: If neither -u or -s is present, Will print the workflow yaml.
    If -u is present, will print the workflow ID to stdout.
    If -s is present, will print the run ID to stdout.
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
        upsert=upsert,
        target=target,
        workflow_id=workflow_id,
        auto_confirm=confirm,
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
@click.option(
    "--is-update-workflow",
    is_flag=True,
    help="Make an 'update' workflow by adding 'since' to the runtime arguments.",
)
@opt_submit
@opt_confirm
@opt_upsert
@opt_workflow_id
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
    confirm: bool = False,
    upsert: bool = False,
    workflow_id: Optional[str] = None,
    is_update_workflow: bool = False,
) -> None:
    """Generate the workflow to create and ingest items.

    Read the asset paths from the chunk file at CHUNK and
    submit a workflow to process into items and ingest into
    the database.

    Use -u or --upsert to upsert the workflow through the API.
    Use -s or --submit to upsert and submit the workflow through the API.

    Output: If neither -u or -s is present, Will print the workflow yaml.
    If -u is present, will print the workflow ID to stdout.
    If -s is present, will print the run ID to stdout.
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
        upsert=upsert,
        workflow_id=workflow_id,
        is_update_workflow=is_update_workflow,
        auto_confirm=confirm,
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
@opt_confirm
@opt_upsert
@opt_workflow_id
@click.pass_context
def ingest_collection_cmd(
    ctx: click.Context,
    dataset: Optional[str],
    collection: Optional[str],
    arg: List[Tuple[str, str]] = [],
    target: Optional[str] = None,
    submit: bool = False,
    confirm: bool = False,
    upsert: bool = False,
    workflow_id: Optional[str] = None,
) -> None:
    """Generate the workflow to ingest a collection.

    This will read a collection JSON or template directory,
    specified by the "template" property of the collection
    configuration of the dataset YAML.

    Use -u or --upsert to upsert the workflow through the API.
    Use -s or --submit to upsert and submit the workflow through the API.

    Output: If neither -u or -s is present, Will print the workflow yaml.
    If -u is present, will print the workflow ID to stdout.
    If -s is present, will print the run ID to stdout.
    """
    from . import _cli

    return _cli.ingest_collection_cmd(
        ctx,
        dataset,
        collection,
        arg=arg,
        target=target,
        submit=submit,
        upsert=upsert,
        workflow_id=workflow_id,
        auto_confirm=confirm,
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


@click.command("validate-collection")
@click.argument("collection", type=click.File("rt"))
def validate_collection(collection: click.File) -> None:
    """Validate a STAC collection."""
    from . import _cli

    _cli.validate_collection_cmd(collection)


dataset_cmd.add_command(create_splits_cmd)
dataset_cmd.add_command(create_chunks_cmd)
dataset_cmd.add_command(process_items_cmd)
dataset_cmd.add_command(ingest_collection_cmd)
dataset_cmd.add_command(list_collections_cmd)
dataset_cmd.add_command(validate_collection)
