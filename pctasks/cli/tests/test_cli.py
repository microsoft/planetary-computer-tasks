from click.testing import CliRunner

from pctasks.cli.cli import pctasks_cmd
from pctasks.cli.version import __version__


def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(pctasks_cmd, ["--version"])
    assert result.output == f"pctasks, version {__version__}\n"


def test_direct_invoke():
    result = pctasks_cmd.main(["--version"], standalone_mode=False)
    assert result == 0
