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


@dataclass
class SortParams:
    sort_by: Optional[str]
    desc: bool = True

    def add_sort(self, query: str) -> str:
        if self.sort_by:
            query += f" ORDER BY c.{self.sort_by}"
            if self.desc:
                query += " DESC"
            else:
                query += " ASC"
        return query

    @staticmethod
    def dependency(
        sort_by: Optional[str] = Query(
            None,
            alias="sortBy",
            description="Property to sort results by",
            regex=r"^[a-zA-Z0-9_\.]+$",
        ),
        desc: bool = Query(True, description="Sort results in descending order"),
    ) -> "SortParams":
        return SortParams(sort_by, desc)
