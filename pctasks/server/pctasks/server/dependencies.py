from dataclasses import dataclass
from typing import Optional

from fastapi import Query


@dataclass
class PageParams:
    token: Optional[str]
    limit: int

    @staticmethod
    def dependency(
        page_token: Optional[str] = Query(
            None,
            alias="pageToken",
            description="Continuation token for the next page of results",
        ),
        page_limit: int = Query(
            100, alias="pageLimit", description="Number of records to return"
        ),
    ) -> "PageParams":
        return PageParams(page_token, page_limit)
