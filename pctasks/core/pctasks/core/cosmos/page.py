from typing import Iterable, Iterator, Optional, TypeVar

T = TypeVar("T")


class Page(Iterable[T]):
    def __init__(self, items: Iterable[T], continuation_token: Optional[str]):
        self._items = items
        self._continuation_token = continuation_token

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    @property
    def continuation_token(self) -> Optional[str]:
        return self._continuation_token
