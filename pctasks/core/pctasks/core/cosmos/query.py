# from dataclasses import dataclass
# from typing import List, Optional


# @dataclass
# class OrderBy:
#     field: str
#     ascending: bool = True


# class SQLQuery:
#     """Class for handling SQL Queries."""

#     def __init__(
#         self,
#         select_clause: Optional[List[str]] = None,
#         from_clause: Optional[str] = None,
#         where_clause: Optional[List[str]] = None,
#         order_by_clause: Optional[List[OrderBy]] = None,
#     ) -> None:
#         ...

#     @classmethod
#     def from_string(cls, query: str) -> "SQLQuery":
#         query = query.upper()

#         select_clause: Optional[str] = None
#         from_clause: Optional[str] = None
#         where_cluase: Optional[List[str]] = None
#         order_by_clause: Optional[List[OrderBy]] = None

#         if "ORDER BY" in query:
#             order_by_clause = []
#             split = query.split("ORDER BY")
#             query = split[0]
#             ob = split[1]
#             for ob_part in ob.split(","):
#                 ob_sub_part = ob_part.split(" ")
#                 order_by_clause.append(
#                     OrderBy(
#                         field=ob_sub_part[0],
#                         ascending=ob_sub_part[1] == "ASC"
#                         if len(ob_sub_part) > 1
#                         else True,
#                     )
#                 )

#         if "WHERE" in query:
#             where_clause = []
#             split = query.split("WHERE")
#             query = split[0]
#             where = split[1]


#         if "FROM" in query:
#             split = query.split("FROM")
#             query = split[0]
#             from_clause = split[1]


#         return cls(query)
