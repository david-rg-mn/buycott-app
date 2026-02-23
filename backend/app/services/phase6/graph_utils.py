from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


def graph_adjacency(graph: dict[str, Any]) -> dict[str, set[str]]:
    adjacency: dict[str, set[str]] = defaultdict(set)
    edges = graph.get("edges") if isinstance(graph, dict) else []
    if not isinstance(edges, list):
        return adjacency
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        adjacency[source].add(target)
        adjacency[target].add(source)
    return adjacency


def build_on_demand_subgraph(graph: dict[str, Any], seed_nodes: set[str], max_hops: int = 2) -> dict[str, Any]:
    adjacency = graph_adjacency(graph)
    node_payload = {node.get("id"): node for node in graph.get("nodes", []) if isinstance(node, dict)}

    included_nodes: set[str] = set()
    queue: deque[tuple[str, int]] = deque((seed, 0) for seed in seed_nodes if seed)
    seen_depth: dict[str, int] = {seed: 0 for seed in seed_nodes if seed}

    while queue:
        node, depth = queue.popleft()
        included_nodes.add(node)
        if depth >= max_hops:
            continue
        for nxt in adjacency.get(node, set()):
            next_depth = depth + 1
            prev = seen_depth.get(nxt)
            if prev is not None and prev <= next_depth:
                continue
            seen_depth[nxt] = next_depth
            queue.append((nxt, next_depth))

    edges = []
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source in included_nodes and target in included_nodes:
            edge_hops = int(edge.get("hops") or 1)
            if edge_hops <= max_hops:
                edges.append(edge)

    nodes = [node_payload[node_id] for node_id in sorted(included_nodes) if node_id in node_payload]
    return {
        "max_hops": max_hops,
        "seed_nodes": sorted(seed_nodes),
        "nodes": nodes,
        "edges": edges,
    }
