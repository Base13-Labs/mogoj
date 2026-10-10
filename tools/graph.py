#!/usr/bin/env python3
"""
Mogoj Graph — build and query a doc relationship graph from the context index.

Docs are nodes, shared keywords are edges. No external dependencies.

Commands:
  build               Build graph.json from context-index.json
  neighbors <doc>     Show docs connected to a given doc
  path <doc1> <doc2>  Find shortest path between two docs
  clusters            Show clusters of related docs
"""

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

# Import shared utilities
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    INDEX_JSON, GRAPH_JSON,
    load_json, save_json, mogoj_main, PrereqError,
)


def load_index():
    data = load_json(INDEX_JSON)
    if data is None:
        raise PrereqError(f"Index not found: {INDEX_JSON}\nRun 'python tools/index.py build' first.")
    return data


def load_graph():
    data = load_json(GRAPH_JSON)
    if data is None:
        raise PrereqError(f"Graph not found: {GRAPH_JSON}\nRun 'python tools/graph.py build' first.")
    return data


def build_graph_data(index):
    """Build adjacency data from the keyword index."""
    doc_keywords = defaultdict(set)
    for kw, docs in index.items():
        for d in docs:
            doc_keywords[d].add(kw)

    nodes = sorted(doc_keywords.keys())
    edges = defaultdict(lambda: defaultdict(list))

    for kw, docs in index.items():
        docs = sorted(set(docs))
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                edges[docs[i]][docs[j]].append(kw)
                edges[docs[j]][docs[i]].append(kw)

    edges_serial = {}
    for doc, neighbors in edges.items():
        edges_serial[doc] = {n: sorted(kws) for n, kws in neighbors.items()}

    return {
        "nodes": nodes,
        "edges": edges_serial,
        "doc_keywords": {d: sorted(kws) for d, kws in doc_keywords.items()},
    }


def cmd_build(args):
    """Build the graph from context-index.json."""
    index = load_index()
    graph = build_graph_data(index)

    save_json(GRAPH_JSON, graph, sort_keys=False)

    total_edges = sum(len(v) for v in graph["edges"].values()) // 2
    print(f"Graph built: {len(graph['nodes'])} nodes, {total_edges} edges")
    print(f"Saved to {GRAPH_JSON}")


def find_doc(graph, query):
    """Find a doc in the graph by partial match."""
    query_lower = query.lower()
    if query in graph["nodes"]:
        return query
    matches = [n for n in graph["nodes"] if query_lower in n.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        print(f"Ambiguous query '{query}'. Matches:")
        for m in matches:
            print(f"  - {m}")
        sys.exit(1)
    print(f"Doc not found: '{query}'")
    sys.exit(1)


def cmd_neighbors(args):
    """Show docs connected to a given doc."""
    graph = load_graph()
    doc = find_doc(graph, args.doc)
    edges = graph.get("edges", {}).get(doc, {})

    if not edges:
        print(f"'{doc}' has no connections.")
        return

    sorted_neighbors = sorted(edges.items(), key=lambda x: -len(x[1]))

    print(f"Neighbors of '{doc}' ({len(sorted_neighbors)} connections):\n")
    for neighbor, keywords in sorted_neighbors:
        kw_str = ", ".join(keywords[:5])
        if len(keywords) > 5:
            kw_str += f" (+{len(keywords) - 5} more)"
        print(f"  [{len(keywords):2d} shared] {neighbor}")
        print(f"           via: {kw_str}")


def cmd_path(args):
    """Find shortest path between two docs via BFS."""
    graph = load_graph()
    doc1 = find_doc(graph, args.doc1)
    doc2 = find_doc(graph, args.doc2)

    if doc1 == doc2:
        print("Same document.")
        return

    edges = graph.get("edges", {})

    visited = {doc1}
    queue = deque([(doc1, [doc1])])

    while queue:
        current, path = queue.popleft()
        neighbors = edges.get(current, {})
        for neighbor in sorted(neighbors.keys()):
            if neighbor == doc2:
                full_path = path + [neighbor]
                print(f"Path found ({len(full_path) - 1} hop{'s' if len(full_path) - 1 != 1 else ''}):\n")
                for i, node in enumerate(full_path):
                    print(f"  {'  ' * i}{node}")
                    if i < len(full_path) - 1:
                        shared = edges.get(node, {}).get(full_path[i + 1], [])
                        print(f"  {'  ' * i}  -- via: {', '.join(shared[:5])}")
                return
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    print(f"No path found between '{doc1}' and '{doc2}'.")


def cmd_clusters(args):
    """Find clusters of related docs using connected components."""
    graph = load_graph()
    edges = graph.get("edges", {})
    nodes = set(graph.get("nodes", []))

    visited = set()
    clusters = []

    for node in sorted(nodes):
        if node in visited:
            continue
        component = []
        queue = deque([node])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            component.append(current)
            for neighbor in edges.get(current, {}):
                if neighbor not in visited:
                    queue.append(neighbor)
        clusters.append(sorted(component))

    clusters.sort(key=lambda c: -len(c))

    print(f"Found {len(clusters)} cluster(s):\n")
    for i, cluster in enumerate(clusters, 1):
        hub = max(cluster, key=lambda d: len(edges.get(d, {}))) if edges else cluster[0]
        hub_connections = len(edges.get(hub, {}))

        print(f"Cluster {i} ({len(cluster)} docs, hub: {hub} [{hub_connections} connections]):")
        for doc in cluster:
            conn = len(edges.get(doc, {}))
            print(f"  [{conn:2d}] {doc}")
        print()


@mogoj_main
def main():
    parser = argparse.ArgumentParser(
        description="Mogoj Graph — doc relationship graph from context index",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python tools/graph.py build\n"
               "  python tools/graph.py neighbors chatx.md\n"
               "  python tools/graph.py path chatx.md packman.md\n"
               "  python tools/graph.py clusters\n",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("build", help="Build graph.json from context-index.json")

    p_neighbors = sub.add_parser("neighbors", help="Show connected docs")
    p_neighbors.add_argument("doc", help="Doc path or partial name")

    p_path = sub.add_parser("path", help="Find shortest path between two docs")
    p_path.add_argument("doc1", help="Start doc")
    p_path.add_argument("doc2", help="End doc")

    sub.add_parser("clusters", help="Show clusters of related docs")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "build": cmd_build,
        "neighbors": cmd_neighbors,
        "path": cmd_path,
        "clusters": cmd_clusters,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
