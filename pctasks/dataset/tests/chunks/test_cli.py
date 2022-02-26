from pathlib import Path

from pctasks.dev.test_utils import run_pctasks

HERE = Path(__file__).parent


def test_naip_dry_run():
    dataset = HERE / ".." / "data-files" / "datasets" / "naip.yaml"

    chunkset_id = "test-chunkset"

    run_pctasks(
        ["-v", "dataset", "create-chunks", "-n", "--dataset", str(dataset), chunkset_id]
    )
