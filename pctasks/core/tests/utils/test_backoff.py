import pytest
import requests.exceptions
import azure.core.exceptions

from pctasks.core.utils.backoff import with_backoff


@pytest.mark.parametrize('kind', [
    TimeoutError,
    requests.exceptions.ConnectionError,
    azure.core.exceptions.IncompleteReadError,
])
def test_retry_timeout_errors(kind):

    i = 0

    def make_callable(kind):

        def fn():
            nonlocal i
            i += 1

            if i > 2:
                return True
            else:
                raise kind()
        return fn
        

    result = with_backoff(make_callable(kind))
    assert i == 3
    assert result is True

