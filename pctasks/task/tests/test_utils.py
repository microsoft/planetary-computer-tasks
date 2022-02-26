from pctasks.dataset.chunks.task import create_chunks_task
from pctasks.task.utils import get_task_path


class TestTaskHolder:
    task = create_chunks_task


def test_get_object_path_in_package():
    task_path = get_task_path(create_chunks_task, "create_chunks_task")
    assert task_path == "pctasks.dataset.chunks.task:create_chunks_task"


def test_get_task_path_in_class():
    task_path = get_task_path(
        TestTaskHolder.task, "TestTaskHolder.task", module=TestTaskHolder.__module__
    )
    assert task_path == "tests.test_utils:TestTaskHolder.task"
