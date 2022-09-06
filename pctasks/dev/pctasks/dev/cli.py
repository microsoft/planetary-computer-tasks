import argparse
import logging
import sys
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union

from pctasks.dev.setup_azurite import clear_records, setup_azurite
from pctasks.task.version import __version__

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _setup_logging(level: Union[str, int], log_libraries: bool = False) -> None:
    _logger = logging.root if log_libraries else logging.getLogger("pctasks")

    _logger.setLevel(level)

    if log_libraries:
        formatter = logging.Formatter("[%(levelname)s]:%(name)s: %(message)s")
    else:
        formatter = logging.Formatter("[%(levelname)s]:%(asctime)s: %(message)s")

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(level)
    ch.setFormatter(formatter)
    _logger.addHandler(ch)


def setup_azurite_cmd(args: Dict[str, Any]) -> int:
    setup_azurite()
    return 0


def clear_records_cmd(args: Dict[str, Any]) -> int:
    clear_records()
    return 0


def parse_args(args: List[str]) -> Optional[Dict[str, Any]]:
    desc = "Planetary Computer Tasks - Dev tools"
    dhf = argparse.ArgumentDefaultsHelpFormatter
    parser0 = argparse.ArgumentParser(description=desc)
    parser0.add_argument(
        "--version",
        help="Print version and exit",
        action="version",
        version=__version__,
    )

    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--logging", default="INFO", help="DEBUG, INFO, WARN, ERROR, CRITICAL"
    )
    parent.add_argument(
        "--log-libs", action="store_true", help="Output logs from other libraries"
    )

    subparsers = parser0.add_subparsers(dest="command")

    # setup-azurite command
    _ = subparsers.add_parser(
        "setup-azurite",
        help="Sets up Azurite for development.",
        parents=[parent],
        formatter_class=dhf,
    )

    # clear-records command
    _ = subparsers.add_parser(
        "clear-records",
        help="Clears Azurite records.",
        parents=[parent],
        formatter_class=dhf,
    )

    parsed_args = {
        k: v for k, v in vars(parser0.parse_args(args)).items() if v is not None
    }

    if "command" not in parsed_args:
        parser0.print_usage()
        return None

    return parsed_args


def cli(args: Optional[List[str]] = None) -> Optional[int]:
    parsed_args = parse_args(args or sys.argv[1:])

    if not parsed_args:
        return None

    loglevel = parsed_args.pop("logging")
    _setup_logging(loglevel, parsed_args.pop("log_libs", False))

    cmd = parsed_args.pop("command")

    if cmd == "setup-azurite":
        return setup_azurite_cmd(parsed_args)
    if cmd == "clear-records":
        return clear_records_cmd(parsed_args)
    return None


if __name__ == "__main__":
    return_code = cli()
    if return_code is not None and return_code != 0:
        sys.exit(return_code)
