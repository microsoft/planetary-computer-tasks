from typing import List, Optional

import click

from pctasks.core.constants import MICROSOFT_OWNER
from pctasks.ingest.constants import DEFAULT_INSERT_GROUP_SIZE


@click.command("ndjsons")
@click.argument("collection_id")
@click.argument("ndjson_folder_uri")
@click.option("-t", "--target", help="Target environment to ingest into.")
@click.option(
    "--insert-group-size",
    type=int,
    default=DEFAULT_INSERT_GROUP_SIZE,
    show_default=True,
    help="Number of items to insert into the database per bulk load.",
)
@click.option(
    "--num-workers",
    help="The number of workers to use for ingest. Defaults to the number of cores.",
)
@click.option(
    "--work-mem",
    help="The work_mem setting (in MB) to use for this ingest.",
)
@click.option(
    "--insert-only",
    is_flag=True,
    help=(
        "Run INSERT for ingest. Fails on conflicting item IDs. "
        "By default, ingest will run a (slower) upsert operation."
    ),
)
@click.option("--owner", help="The owner of the collection.", default=MICROSOFT_OWNER)
@click.option("-e", "--extension", multiple=True, help="File extensions to include.")
@click.option(
    "--name-starts-with", help="Only include files that start with this string."
)
@click.option("--ends-with", help="Only include files that end with this string.")
@click.option("--matches", help="Only include files that match this regex.")
@click.option("--limit", type=int, help="Limit the number of ndjson files to ingest.")
@click.option("-s", "--submit", is_flag=True, help="Submit the workflow.")
@click.pass_context
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
) -> None:
    """Ingest Items from a folder of Ndjsons.

    Ingest NDJson files from the folder at NDJSON_FOLDER_URI containing items for
    collection COLLECTION_ID into target environment TARGET.

    This command will print the workflow to stdout, and submit it if the --submit
    flag is provided. If submitted, stdout will contain the run ID for the workflow.
    """
    from . import _cli

    return _cli.ingest_ndjson_cmd(
        ctx,
        collection_id,
        ndjson_folder_uri,
        target,
        insert_group_size,
        insert_only,
        num_workers,
        work_mem,
        extension,
        name_starts_with,
        ends_with,
        matches,
        owner,
        submit,
        limit,
    )


@click.command("collection")
@click.argument("path", type=click.Path(exists=True))
@click.option("-t", "--target", help="Target environment to ingest into.")
@click.option("--owner", help="The owner of the collection.", default=MICROSOFT_OWNER)
@click.option("-s", "--submit", is_flag=True, help="Submit the workflow.")
@click.pass_context
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
    from . import _cli

    return _cli.ingest_collection_cmd(ctx, path, target, owner, submit)


@click.group("ingest")
def ingest_cmd() -> None:
    """PCTasks commands for ingesting STAC objects into a database."""
    pass


ingest_cmd.add_command(ingest_ndjson_cmd)
ingest_cmd.add_command(ingest_collection_cmd)
