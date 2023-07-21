import pytest
from kubernetes.client.models import V1ResourceRequirements

import pctasks.core.models.task
import pctasks.run.workflow.kubernetes
from pctasks.dev.k8s import get_streaming_task_definition
from pctasks.task.streaming import Resources


def test_get_deployment_name():
    task_definition = get_streaming_task_definition()
    result = pctasks.run.workflow.kubernetes.get_deployment_name(task_definition)
    assert result == "devstoreaccount1-test-deployment"


@pytest.mark.parametrize("allow_spot_instances", [True, False])
def test_build_streaming_deployment(allow_spot_instances):
    task_definition = get_streaming_task_definition()
    if allow_spot_instances:
        task_definition.args["streaming_options"]["allow_spot_instances"] = True

    result = pctasks.run.workflow.kubernetes.build_streaming_deployment(
        task_definition,
        input_uri="blob://pctasksteststaging/input",
        taskio_tenant_id="test-tenant-id",
        taskio_client_id="test-client-id",
        taskio_client_secret="test-client-secret",
        node_group="pc-lowlatency",
    )
    labels = {
        "node_group": "pc-lowlatency",
        "planetarycomputer.microsoft.com/queue_url": "devstoreaccount1-test",
        "planetarycomputer.microsoft.com/task_type": "streaming",
    }

    assert result.metadata.name == "devstoreaccount1-test-deployment"
    assert result.metadata.labels == labels
    assert result.spec.selector["matchLabels"] == labels
    assert result.spec.template.metadata.labels == labels
    assert result.spec.template.spec.service_account_name == "default"
    assert result.spec.template.spec.containers[0].image == task_definition.image
    assert result.spec.template.spec.containers[0].args == [
        "task",
        "run",
        "blob://pctasksteststaging/input",
    ]

    if allow_spot_instances:
        assert result.spec.template.spec.affinity.to_dict() == {
            "node_affinity": {
                "preferred_during_scheduling_ignored_during_execution": [
                    {
                        "preference": {
                            "match_expressions": [
                                {
                                    "key": "kubernetes.azure.com/scalesetpriority",
                                    "operator": "In",
                                    "values": ["spot"],
                                }
                            ],
                            "match_fields": None,
                        },
                        "weight": 1,
                    }
                ],
                "required_during_scheduling_ignored_during_execution": {
                    "node_selector_terms": [
                        {
                            "match_expressions": [
                                {
                                    "key": "node_group",
                                    "operator": "In",
                                    "values": ["pc-lowlatency"],
                                }
                            ],
                            "match_fields": None,
                        }
                    ]
                },
            },
            "pod_affinity": None,
            "pod_anti_affinity": None,
        }


def test_build_streaming_scaler():
    task_definition = get_streaming_task_definition()
    result = pctasks.run.workflow.kubernetes.build_streaming_scaler(task_definition)
    assert result["metadata"]["name"] == "devstoreaccount1-test-scaler"
    assert (
        result["spec"]["scaleTargetRef"]["name"] == "devstoreaccount1-test-deployment"
    )
    assert result["spec"]["minReplicaCount"] == 0
    assert result["spec"]["maxReplicaCount"] == 10
    assert result["spec"]["pollingInterval"] == 30
    assert result["spec"]["triggers"][0]["metadata"]["queueName"] == "test"
    assert result["spec"]["triggers"][0]["metadata"]["queueLength"] == "100"
    assert (
        result["spec"]["triggers"][0]["metadata"]["accountName"] == "devstoreaccount1"
    )


def test_get_deployment_name_azurite():
    task_definition = get_streaming_task_definition()
    task_definition.args["streaming_options"][
        "queue_url"
    ] = "http://localhost:10001/devstoreaccount1/test-queue-stream"
    result = pctasks.run.workflow.kubernetes.get_deployment_name(task_definition)
    assert result == "localhost.10001-devstoreaccount1.test-queue-stream-deployment"


def test_extra_env():
    # We might be able to remove the extra_env concept completely, in which case
    # remove this test. For now we need it to bootstrap some variables before
    # pctasks' built-in env variable management kicks in.
    task_definition = get_streaming_task_definition()
    task_definition.args["extra_env"] = {"MY_KEY": "MY_VALUE"}

    result = pctasks.run.workflow.kubernetes.build_streaming_deployment(
        task_definition,
        input_uri="blob://pctasksteststaging/input",
        taskio_tenant_id="test-tenant-id",
        taskio_client_id="test-client-id",
        taskio_client_secret="test-client-secret",
        node_group="pc-lowlatency",
    )
    env = result.spec.template.spec.containers[0].env
    for var in env:
        if var.name == "MY_KEY":
            assert var.value == "MY_VALUE"
            break
    else:
        raise AssertionError("MY_KEY not found in env")


def test_build_resources():
    resources = Resources(
        limits={
            "cpu": "1",
            "memory": "1Gi",
        },
        requests={
            "cpu": "0.5",
            "memory": "512Mi",
        },
    )
    result = pctasks.run.workflow.kubernetes.build_resources(resources)
    expected = V1ResourceRequirements(
        limits={
            "cpu": "1",
            "memory": "1Gi",
        },
        requests={
            "cpu": "0.5",
            "memory": "512Mi",
        },
    )

    assert result == expected
