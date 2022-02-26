from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from planetary_computer.sas import get_token

from pctasks.core.models.task import CompletedTaskResult
from pctasks.dataset.chunks.models import CreateChunksOutput
from pctasks.dataset.chunks.task import CreateChunksInput, create_chunks_task
from pctasks.dev.task import run_test_task
from pctasks.task.utils import get_task_path

HERE = Path(__file__)
TEST_ASSETS_PATH = HERE.parent.parent / "data-files" / "test-assets"

NAIP_SA = "naipeuwest"
NAIP_CONTAINER = "naip"


def test_task():
    src_storage_uri = str(TEST_ASSETS_PATH)

    with TemporaryDirectory() as tmp_dir:
        args = CreateChunksInput(
            src_storage_uri=src_storage_uri,
            dst_storage_uri=tmp_dir,
            chunk_length=2,
            name_starts_with=None,
            since=None,
            limit=None,
            extensions=None,
            ends_with=None,
            matches=None,
            chunk_prefix="test-chunk-",
        )

        task_path = get_task_path(create_chunks_task, "create_chunks_task")

        task_result = run_test_task(args.dict(), task_path)
        assert isinstance(task_result, CompletedTaskResult)

        result = CreateChunksOutput.parse_obj(task_result.output)

        assert len(result.chunk_uris) == 2
        assert set(result.chunk_uris) == set(
            [
                str(Path(tmp_dir) / "test-chunk-0.csv"),
                str(Path(tmp_dir) / "test-chunk-1.csv"),
            ]
        )

        for chunk_uri in result.chunk_uris:
            with open(chunk_uri) as f:
                for line in f:
                    assert Path(line).exists


def test_naip_since_date():
    """
    This test is predicated on the fact that the
    files with the below prefix were either
    last modified on 11/17/2020 and the other
    on 2/22/2021. The later modified files are all
    COGs that were recreated, and are the only .tif
    files. If this changes in the future
    it will break this test.
    """
    FOLDER_PREFIX = "v002/al/2011/al_100cm_2011/30085"
    since_date = date.fromisoformat("2021-01-01")

    src_storage_uri = f"blob://{NAIP_SA}/{NAIP_CONTAINER}/{FOLDER_PREFIX}"

    with TemporaryDirectory() as tmp_dir:
        args = CreateChunksInput(
            src_storage_uri=src_storage_uri,
            src_sas=get_token("naipeuwest", "naip").token,
            dst_storage_uri=tmp_dir,
            chunk_length=1,
            since=datetime.combine(since_date, datetime.min.time()),
            chunk_prefix="test-chunk-",
        )

        task_path = get_task_path(create_chunks_task, "create_chunks_task")

        task_result = run_test_task(args.dict(), task_path)
        assert isinstance(task_result, CompletedTaskResult)

        result = CreateChunksOutput.parse_obj(task_result.output)

        assert len(result.chunk_uris) == 12
        for chunk_uri in result.chunk_uris:
            with open(chunk_uri) as f:
                for line in f:
                    assert line.endswith(".tif")
