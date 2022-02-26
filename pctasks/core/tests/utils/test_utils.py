from pctasks.core.utils import completely_flatten


def test_completely_flatten():
    assert list(completely_flatten([])) == []
    assert list(completely_flatten([1, 2, 3])) == [1, 2, 3]
    assert list(completely_flatten([1, [2, 3], 4])) == [1, 2, 3, 4]
    assert list(completely_flatten([1, [2, [3, 4]], 5])) == [1, 2, 3, 4, 5]
