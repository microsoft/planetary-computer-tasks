import pytest

from pctasks.core.models.task import TaskDefinition
from pctasks.core.models.workflow import JobDefinition, WorkflowDefinition
from pctasks.dataset.workflow import modify_for_update


@pytest.fixture
def minimal_workflow() -> WorkflowDefinition:
    """Create a minimal workflow for testing."""
    return WorkflowDefinition(
        name="Test Workflow",
        dataset_id="test-dataset",
        args=None,
        jobs={
            "create-splits": JobDefinition(
                id="create-splits",
                tasks=[
                    TaskDefinition(
                        id="create-splits-task",
                        task="test.task",
                        image="test:latest",
                        args={"inputs": [{"chunk_options": {}}]},
                    )
                ],
            ),
            "create-chunks": JobDefinition(
                id="create-chunks",
                tasks=[
                    TaskDefinition(
                        id="create-chunks-task",
                        task="test.task",
                        image="test:latest",
                        args={"dst_uri": "blob://account/container/chunks/test/assets"},
                    )
                ],
            ),
            "process-chunk": JobDefinition(
                id="process-chunk",
                tasks=[
                    TaskDefinition(
                        id="create-items",
                        task="test.task",
                        image="test:latest",
                        args={
                            "item_chunkset_uri": "blob://account/container/chunks/test/items"  # noqa: E501
                        },
                    )
                ],
            ),
        },
    )


def test_modify_for_update_with_none_args(minimal_workflow: WorkflowDefinition) -> None:
    modified = modify_for_update(minimal_workflow)

    assert modified.args == ["since"]
    assert isinstance(modified.args, list)


def test_modify_for_update_with_list_args_no_since(
    minimal_workflow: WorkflowDefinition,
) -> None:
    minimal_workflow.args = ["name", "force"]
    modified = modify_for_update(minimal_workflow)

    assert modified.args == ["name", "force", "since"]
    assert isinstance(modified.args, list)


def test_modify_for_update_with_list_args_has_since(
    minimal_workflow: WorkflowDefinition,
) -> None:
    minimal_workflow.args = ["name", "since", "force"]
    modified = modify_for_update(minimal_workflow)

    # Should not duplicate 'since'
    assert modified.args == ["name", "since", "force"]
    assert isinstance(modified.args, list)


def test_modify_for_update_with_dict_args_no_since(
    minimal_workflow: WorkflowDefinition,
):
    minimal_workflow.args = {"name": "world", "force": False}
    modified = modify_for_update(minimal_workflow)

    # Should add 'since' to dict
    assert modified.args == {"name": "world", "force": False, "since": None}
    assert isinstance(modified.args, dict)


def test_modify_for_update_with_dict_args_has_since(
    minimal_workflow: WorkflowDefinition,
):
    minimal_workflow.args = {"name": "world", "since": "2023-01-01", "force": False}

    modified = modify_for_update(minimal_workflow)

    assert modified.args == {"name": "world", "since": "2023-01-01", "force": False}
    assert isinstance(modified.args, dict)


def test_modify_for_update_workflow_modifications(
    minimal_workflow: WorkflowDefinition,
) -> None:
    modified = modify_for_update(minimal_workflow)

    assert "since" in modified.args

    splits_args = modified.jobs["create-splits"].tasks[0].args
    assert splits_args["inputs"][0]["chunk_options"]["since"] == "${{ args.since }}"

    chunks_dst_uri = modified.jobs["create-chunks"].tasks[0].args["dst_uri"]
    assert "${{ args.since }}" in chunks_dst_uri
    assert (
        chunks_dst_uri
        == "blob://account/container/chunks/test/${{ args.since }}/assets"
    )

    items_uri = modified.jobs["process-chunk"].tasks[0].args["item_chunkset_uri"]
    assert "${{ args.since }}" in items_uri
    assert items_uri == "blob://account/container/chunks/test/${{ args.since }}/items"


def test_modify_for_update_preserves_original(
    minimal_workflow: WorkflowDefinition,
) -> None:
    minimal_workflow.args = ["name", "force"]
    original_args = minimal_workflow.args
    original_chunks_uri = (
        minimal_workflow.jobs["create-chunks"].tasks[0].args["dst_uri"]
    )

    modified = modify_for_update(minimal_workflow)

    assert minimal_workflow.args == original_args
    assert (
        minimal_workflow.jobs["create-chunks"].tasks[0].args["dst_uri"]
        == original_chunks_uri
    )

    assert modified.args == ["name", "force", "since"]
    assert (
        "${{ args.since }}" in modified.jobs["create-chunks"].tasks[0].args["dst_uri"]
    )
