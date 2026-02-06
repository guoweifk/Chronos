#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
@author: GW
@time: 2025-11-14 17:01 
@file: get_min_graph.py
@project: GW_My_tools
@describe: Powered By GW
"""
from collections import deque
from typing import Dict, Set, Iterable, Tuple
# from .base_graph import INFRA_NODES
Graph = Dict[str, Set[str]]

# 标记“基础设施类节点”，默认不作为中间节点参与最小路径计算
INFRA_NODES = {"MONGO", "MYSQL", "METRICS", "WEBUI", "DNS"}
def build_undirected(g: Graph) -> Graph:
    """把上面的有向/半向图转成无向图，方便做最短路径。"""
    ug: Graph = {n: set() for n in g}
    for u, nbrs in g.items():
        for v in nbrs:
            ug.setdefault(u, set()).add(v)
            ug.setdefault(v, set()).add(u)
    return ug


def _shortest_path_filtered(
    ug: Graph,
    start: str,
    goal: str,
    forbidden_intermediate: Set[str],
    terminals: Set[str],
) -> Iterable[str]:
    """
    在无向图 ug 上求 start -> goal 的最短路径，
    但不允许 forbidden_intermediate 这些点作为中间节点
    （如果它本身就是终点之一，则允许）。
    """
    if start == goal:
        return [start]

    q = deque([start])
    parent = {start: None}

    while q:
        u = q.popleft()
        for v in ug.get(u, []):
            # v 是中间节点时，如果在 forbidden 集合里就跳过
            if v in forbidden_intermediate and v not in terminals and v != goal:
                continue
            if v not in parent:
                parent[v] = u
                if v == goal:
                    # 回溯出路径
                    path = [v]
                    while parent[path[-1]] is not None:
                        path.append(parent[path[-1]])
                    return list(reversed(path))
                q.append(v)
    return []  # 不连通，则返回空路径


def minimal_subgraph(
    full_graph: Graph,
    selected_nodes: Iterable[str],
    forbidden_intermediate: Iterable[str] = INFRA_NODES,
) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    """
    给定全局图 full_graph 和若干目标节点 selected_nodes，
    返回：
      - sub_nodes: 这个最小子图里的所有节点
      - sub_edges: 这个最小子图里的所有无向边 (u, v)（u < v）

    forbidden_intermediate: 默认不允许这些节点当中间节点（但可作为终点）。
    """
    ug = build_undirected(full_graph)
    selected = [n for n in selected_nodes if n in full_graph]
    if not selected:
        return set(), set()

    forbidden_set = set(forbidden_intermediate)
    terminals = set(selected)

    sub_nodes: Set[str] = set(selected)
    sub_edges: Set[Tuple[str, str]] = set()

    # 对每一对目标节点，求一条最短路径，然后把路径上的点和边加入子图
    for i in range(len(selected)):
        for j in range(i + 1, len(selected)):
            s, t = selected[i], selected[j]
            path = _shortest_path_filtered(ug, s, t, forbidden_set, terminals)
            if not path:
                continue  # 这两个节点不连通，跳过
            for a, b in zip(path, path[1:]):
                sub_nodes.add(a)
                sub_nodes.add(b)
                edge = tuple(sorted((a, b)))
                sub_edges.add(edge)

    return sub_nodes, sub_edges

def one_hop_subgraph(
    full_graph: Graph,
    center: str,
) -> Tuple[Set[str], Set[Tuple[str, str]]]:
    """
    给定一个中心节点 center，返回其一跳邻居子图：
      - sub_nodes: center 本身 + 所有直接相连的节点
      - sub_edges: center 与这些邻居之间的无向边 (u, v)（u < v）
    """
    ug = build_undirected(full_graph)

    if center not in ug:
        return set(), set()

    neighbors = ug[center]
    sub_nodes: Set[str] = {center} | set(neighbors)
    sub_edges: Set[Tuple[str, str]] = set()

    for n in neighbors:
        edge = tuple(sorted((center, n)))
        sub_edges.add(edge)

    return sub_nodes, sub_edges
