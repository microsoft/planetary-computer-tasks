from typing import List

import networkx as nx

from pctasks.core.models.workflow import JobConfig


def sort_jobs(jobs: List[JobConfig]) -> List[JobConfig]:
    G = nx.DiGraph()

    for job in jobs:
        G.add_node(job.get_id())
        for dep in job.get_dependencies() or []:
            G.add_edge(dep, job.get_id())

    sorted_ids: List[str] = list(nx.topological_sort(G))
    return sorted(jobs, key=lambda job: sorted_ids.index(job.get_id()))
