import time
from typing import Any, Callable, Optional

import click


class OperationTimeoutError(Exception):
    pass


def wait_for_operation(
    get_response: Callable[[], Optional[Any]], timeout: int = 60, sleep_time: int = 5
) -> Optional[Any]:
    tic = time.perf_counter()
    toc = time.perf_counter()
    got_response = False
    response: Optional[Any] = None
    while toc - tic < timeout:
        response = get_response()
        if response:
            got_response = True
            break
        toc = time.perf_counter()
        time.sleep(sleep_time)
        click.echo(
            click.style("...still waiting for operation to complete...", fg="yellow")
        )

    if not got_response:
        click.echo(click.style("Operation timed out!", fg="red"))
        return None

    return response
