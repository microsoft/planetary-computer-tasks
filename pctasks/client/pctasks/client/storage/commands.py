from pathlib import Path
from typing import IO, Optional

import click
from rich.console import Console

from pctasks.client.constants import (
    FILE_EXISTS_EXIT_CODE,
    NOT_FOUND_EXIT_CODE,
    UNEXPECTED_ERROR_EXIT_CODE,
)
from pctasks.core.storage import get_storage_for_file


def get_file(
    ctx: click.Context,
    uri: str,
    output: Optional[str],
    force: bool,
    token: Optional[str],
) -> int:
    storage, path = get_storage_for_file(uri, token)
    console = Console(stderr=True)

    file_name = Path(path).name

    output_path: Path
    if output is None:
        output_path = Path.cwd() / file_name
    else:
        output_path = Path(output)
        if output_path.is_dir():
            output_path = output_path / file_name

    if force and not output_path.parent.exists():
        output_path.mkdir(parents=True)

    if output_path.exists() and not force:
        console.print(f"[bold red]File already exists: {output_path}[/bold red]")
        return FILE_EXISTS_EXIT_CODE

    if not storage.file_exists(path):
        console.print(f"[red]File {path} does not exist[/red]")
        return NOT_FOUND_EXIT_CODE

    with console.status("Fetching data...") as fetch_status:
        fetch_status.update(
            status="[bold green]Fetching data...",
            spinner="aesthetic",
            spinner_style="green",
        )

        content = storage.read_bytes(path)

        with output_path.open("wb") as f:
            f.write(content)

    console.print(f"[bold green]File saved to {output_path}[/bold green]")

    return 0


def put_file(
    ctx: click.Context,
    input_file: IO[bytes],
    uri: str,
    force: bool,
    token: Optional[str],
) -> int:
    console = Console(stderr=True)

    if uri.endswith("/"):
        if hasattr(input_file, "name"):
            input_file_name = Path(input_file.name).name
        else:
            console.print(f"[bold red]Cannot determine file name:[/bold red] {uri}")
            return UNEXPECTED_ERROR_EXIT_CODE
        uri = uri + input_file_name

    storage, path = get_storage_for_file(uri, token)

    if storage.file_exists(path) and not force:
        console.print(f"[bold red]File already exists: {uri}[/bold red]")
        return FILE_EXISTS_EXIT_CODE

    with console.status("Uploading data...") as fetch_status:
        fetch_status.update(
            status="[bold green]Uploading data...",
            spinner="aesthetic",
            spinner_style="green",
        )

        storage.write_bytes(path, input_file.read())

    console.print(f"[bold green]File uploaded to {uri}[/bold green]")

    return 0
