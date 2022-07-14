from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from planetary_computer.sas import get_token

from pctasks.core.models.task import CompletedTaskResult
from pctasks.core.models.tokens import ContainerTokens, StorageAccountTokens
from pctasks.dataset.chunks.constants import ALL_CHUNK_PREFIX
from pctasks.dataset.chunks.models import ChunksOutput
from pctasks.dataset.chunks.task import CreateChunksInput, create_chunks_task
from pctasks.dataset.models import ChunkOptions
from pctasks.dev.blob import copy_dir_to_azurite, temp_azurite_blob_storage
from pctasks.dev.test_utils import run_test_task
from pctasks.task.utils import get_task_path

HERE = Path(__file__)
TEST_ASSETS_PATH = HERE.parent.parent / "data-files" / "test-assets"

NAIP_SA = "naipeuwest"
NAIP_CONTAINER = "naip"


def test_task():
    src_storage_uri = str(TEST_ASSETS_PATH)

    with TemporaryDirectory() as tmp_dir:
        args = CreateChunksInput(
            src_uri=src_storage_uri,
            dst_uri=tmp_dir,
            options=ChunkOptions(
                chunk_length=2,
                name_starts_with=None,
                since=None,
                limit=None,
                extensions=None,
                ends_with=None,
                matches=None,
                chunk_file_name="test-chunk",
            ),
        )

        task_path = get_task_path(create_chunks_task, "create_chunks_task")

        task_result = run_test_task(args.dict(), task_path)
        assert isinstance(task_result, CompletedTaskResult)

        result = ChunksOutput.parse_obj(task_result.output)

        test_asset_folder = str(TEST_ASSETS_PATH).strip("/")

        assert len(result.chunks) == 2
        assert set([c.uri for c in result.chunks]) == set(
            [
                str(
                    Path(tmp_dir)
                    / ALL_CHUNK_PREFIX
                    / test_asset_folder
                    / "0"
                    / "test-chunk.csv"
                ),
                str(
                    Path(tmp_dir)
                    / ALL_CHUNK_PREFIX
                    / test_asset_folder
                    / "1"
                    / "test-chunk.csv"
                ),
            ]
        )

        for chunk in result.chunks:
            with open(chunk.uri) as f:
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
            src_uri=src_storage_uri,
            dst_uri=tmp_dir,
            options=ChunkOptions(
                chunk_length=1,
                since=datetime.combine(since_date, datetime.min.time()),
            ),
        )

        task_path = get_task_path(create_chunks_task, "create_chunks_task")

        task_result = run_test_task(
            args.dict(),
            task_path,
            tokens={
                "naipeuwest": StorageAccountTokens(
                    containers={
                        "naip": ContainerTokens(
                            token=get_token("naipeuwest", "naip").token
                        )
                    }
                )
            },
        )
        assert isinstance(task_result, CompletedTaskResult)

        result = ChunksOutput.parse_obj(task_result.output)

        assert len(result.chunks) == 12
        for chunk in result.chunks:
            with open(chunk.uri) as f:
                for line in f:
                    assert line.endswith(".tif")


def test_task_simple_assets() -> None:
    with temp_azurite_blob_storage() as storage:
        copy_dir_to_azurite(
            storage,
            HERE.parent.parent / "data-files" / "simple-assets",
            prefix="assets",
        )

        args = CreateChunksInput(
            src_uri=storage.get_uri("assets/b"),
            dst_uri=storage.get_uri("chunks"),
            options=ChunkOptions(
                chunk_length=1,
            ),
        )

        task_path = get_task_path(create_chunks_task, "create_chunks_task")
        print(args.to_json(indent=2))
        task_result = run_test_task(args.dict(), task_path)

        assert isinstance(task_result, CompletedTaskResult)

        result = ChunksOutput.parse_obj(task_result.output)
        print(result.to_json(indent=2))
        for chunk in result.chunks:
            print(chunk.uri)
            for line in storage.read_text(storage.get_path(chunk.uri)).splitlines():
                assert "/./" not in line
                assert storage.file_exists(storage.get_path(line))


def test_task_list_folders():
    src_storage_uri = str(TEST_ASSETS_PATH.parent / "simple-assets")

    with TemporaryDirectory() as tmp_dir:
        args = CreateChunksInput(
            src_uri=src_storage_uri,
            dst_uri=tmp_dir,
            options=ChunkOptions(
                chunk_length=2,
                name_starts_with=None,
                since=None,
                limit=None,
                extensions=None,
                ends_with=None,
                matches=None,
                chunk_file_name="test-chunk",
                list_folders=True,
                max_depth=3,
            ),
        )

        task_path = get_task_path(create_chunks_task, "create_chunks_task")

        task_result = run_test_task(args.dict(), task_path)
        assert isinstance(task_result, CompletedTaskResult)

        result = ChunksOutput.parse_obj(task_result.output)

        test_asset_folder = str(TEST_ASSETS_PATH.parent / "simple-assets").strip("/")

        assert len(result.chunks) == 1
        assert set([c.uri for c in result.chunks]) == set(
            [
                str(
                    Path(tmp_dir)
                    / ALL_CHUNK_PREFIX
                    / test_asset_folder
                    / "0"
                    / "test-chunk.csv"
                ),
            ]
        )

        for chunk in result.chunks:
            with open(chunk.uri) as f:
                for line in f:
                    assert Path(line).exists
                    assert Path(line.strip()).is_dir()
