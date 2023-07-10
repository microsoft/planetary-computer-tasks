from typing import IO, Optional

import click


@click.group(name="storage")
def storage_cmd() -> None:
    pass


@storage_cmd.command(name="get")  # type: ignore[arg-type]
@click.argument("uri")
@click.option(
    "-o",
    "--output",
    help="Output file path or directory. Defaults to the current directory.",
)
@click.option("-f", "--force", is_flag=True, help="Overwrite existing files")
@click.option("-t", "--token", help="Access token (SAS)")
@click.pass_context
def get_file_command(
    ctx: click.Context,
    uri: str,
    output: Optional[str],
    force: bool,
    token: Optional[str],
) -> None:
    """Downloads a file from the given URI to the local filesystem"""
    from .commands import get_file

    ctx.exit(get_file(ctx, uri=uri, output=output, force=force, token=token))


@storage_cmd.command(name="put")  # type: ignore[arg-type]
@click.argument("input", type=click.File("rb"))
@click.argument("uri")
@click.option("-f", "--force", is_flag=True, help="Overwrite existing files")
@click.option("-t", "--token", help="Access token (SAS)")
@click.pass_context
def put_file_command(
    ctx: click.Context,
    input: IO[bytes],
    uri: str,
    force: bool,
    token: Optional[str],
) -> None:
    """Puts a local file into storage.

    If URI ends with "/", the file is uploaded to a directory
    with the same file name as the input file.
    """
    from .commands import put_file

    ctx.exit(
        put_file(
            ctx,
            input_file=input,
            uri=uri,
            force=force,
            token=token,
        )
    )
