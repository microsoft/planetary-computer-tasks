import os
import warnings
from contextlib import contextmanager
from enum import Enum
from itertools import islice
from typing import Any, Callable, Generator, Iterable, Iterator, List, Optional, TypeVar

from urllib3.exceptions import InsecureRequestWarning

T = TypeVar("T")
U = TypeVar("U")


def map_opt(fn: Callable[[T], U], v: Optional[T]) -> Optional[U]:
    """Maps the value of an option to another value, returning
    None if the input option is None.
    """
    return v if v is None else fn(v)


def flatten(it: Iterable[Iterable[T]]) -> Iterable[T]:
    """Takes e.g. a list of lists and flattens it into a list"""
    return [y for x in it for y in x]


def completely_flatten(it: List[Any]) -> Iterable[Any]:
    """Flatten a List with any level of List elements into a single List"""

    def _walk(_it: List[Any]) -> Iterable[Any]:
        for x in _it:
            if isinstance(x, list):
                for y in _walk(x):
                    yield y
            else:
                yield x

    for item in _walk(it):
        yield item


def grouped(it: Iterable[T], size: int) -> Iterable[Iterable[T]]:
    """Group items in an Iterable into groups of the given size."""
    it = iter(it)
    return iter(lambda: tuple(islice(it, size)), ())


class CountingIterator(Iterator[T]):
    """Wraps an iteratable and keeps track of how
    many items were iterated over.

    Attributes:
        count: The number of times the wrapped
        iterator's  __next__ was called.
    """

    def __init__(self, wrapped: Iterable[T]):
        self._wrapped = iter(wrapped)
        self.counter = 0

    def __iter__(self) -> Iterator[T]:
        return self

    def __next__(self) -> T:
        self.counter += 1
        return self._wrapped.__next__()


class StrEnum(str, Enum):
    """An Enum that is also a string.

    This is useful for defining enum constants that are also
    strings.
    """

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return self.value


@contextmanager
def environment(**kwargs: str) -> Generator[None, None, None]:
    """Temporarily set environment variables inside the context manager and
    fully restore previous environment afterwards
    """
    original_env = {key: os.getenv(key) for key in kwargs}
    os.environ.update(kwargs)
    try:
        yield
    finally:
        for key, value in original_env.items():
            if value is None:
                del os.environ[key]
            else:
                os.environ[key] = value


@contextmanager
def ignore_ssl_warnings() -> Generator[None, None, None]:
    """Temporarily ignore SSL warnings inside the context manager and
    restore warnings afterwards
    """

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=InsecureRequestWarning)
        yield
