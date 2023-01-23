from pctasks.core.models.task import TaskDefinition


def test_submit_message_deserialize_serialize():
    js = {
        "id": "test-task",
        "image": "test",
        "task": "foo.bar:task",
        "args": {},
    }

    msg = TaskDefinition(**js)
    js2 = msg.dict(exclude_none=True)
    msg2 = TaskDefinition(**js2)

    assert msg == msg2
