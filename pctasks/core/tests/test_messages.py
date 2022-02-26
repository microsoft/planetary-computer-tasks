from pctasks.core.models.task import TaskConfig


def test_submit_message_deserialize_serialize():
    js = {
        "id": "test-task",
        "image": "test",
        "task": "foo.bar:task",
        "args": {},
    }

    msg = TaskConfig(**js)
    js2 = msg.dict(exclude_none=True)
    msg2 = TaskConfig(**js2)

    assert msg == msg2
