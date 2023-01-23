import logging
import sys

import click

from pctasks.cli.cli import setup_logging
from pctasks.dev.azurite import azurite_cmd
from pctasks.dev.cosmosdb import cosmosdb_cmd
from pctasks.task.version import __version__

logger = logging.getLogger(__name__)


@click.group(name="pctasks-dev")
@click.version_option(__version__)
@click.option("-v", "--verbose", help=("Use verbose mode"), is_flag=True)
@click.option("-q", "--quiet", help=("Use quiet mode (no output)"), is_flag=True)
@click.option("--log-libs", is_flag=True, help="Output logs from other libraries")
def cli(verbose: bool, quiet: bool, log_libs: bool) -> None:
    """ "Planetary Computer Tasks - Dev tools"""
    logging_level = logging.INFO
    if verbose:
        logging_level = logging.DEBUG
    if quiet:
        logging_level = logging.ERROR

    setup_logging(logging_level)


cli.add_command(azurite_cmd)
cli.add_command(cosmosdb_cmd)


if __name__ == "__main__":
    return_code = cli()
    if return_code is not None and return_code != 0:
        sys.exit(return_code)
