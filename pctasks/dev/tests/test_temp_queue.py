from pctasks.dev.queues import TempQueue


def test_temp_queue_name() -> None:
    name = "test-temp-queue-name"
    with TempQueue(name=name) as queue_client:
        assert queue_client.queue_name == name


def test_temp_queue_suffix() -> None:
    suffix = "test-temp-queue-suffix"
    name = f"test-queue-{suffix}"
    with TempQueue(suffix=suffix) as queue_client:
        assert queue_client.queue_name == name


def test_temp_queue_ignores_existing_resource() -> None:
    name = "test-temp-queue-name"
    with TempQueue(name=name):
        with TempQueue(name=name):
            # No exception
            pass
