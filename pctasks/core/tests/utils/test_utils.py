import unittest.mock

import azure.core.exceptions
import pytest
import requests

from pctasks.core.utils import completely_flatten
from pctasks.core.utils.backoff import BackoffError, with_backoff


def test_completely_flatten():
    assert list(completely_flatten([])) == []
    assert list(completely_flatten([1, 2, 3])) == [1, 2, 3]
    assert list(completely_flatten([1, [2, 3], 4])) == [1, 2, 3, 4]
    assert list(completely_flatten([1, [2, [3, 4]], 5])) == [1, 2, 3, 4, 5]


def test_backoff():
    def f():
        request = requests.Request()
        response = requests.Response()
        response.request = request
        response.status_code = 502
        raise requests.HTTPError("502 Error", request=request, response=response)

    # Mock time.sleep to keep the test fast
    with unittest.mock.patch("pctasks.core.utils.backoff.time.sleep"):
        with pytest.raises(BackoffError):
            with_backoff(f)


def test_backoff_incomplete_read_error():
    def f():
        raise azure.core.exceptions.IncompleteReadError()

    # Mock time.sleep to keep the test fast
    with unittest.mock.patch("pctasks.core.utils.backoff.time.sleep"):
        with pytest.raises(BackoffError):
            with_backoff(f)
