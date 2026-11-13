"""Load the lineage graph as an igraph object.

Every analysis script (rq1.py ... rq4.py, baseline.py) starts with:

    from graph_io import load_graph
    g, nodes = load_graph()                    # G_full
    g, nodes = load_graph(with_merges=False)   # G_nomerge

Vertex i of the graph is row i of the node table (column "node").
Edge direction is child -> parent, so:
    g.degree(mode="in")   = number of children
    g.degree(mode="out")  = number of parents
"""

import igraph as ig
import polars as pl

EDGES = "data/processed/edges.parquet"
GRAPH_NODES = "data/processed/graph_nodes.parquet"


def load_graph(with_merges: bool = True):
    """Return (graph, node table).

    with_merges=False drops every edge whose child is a merge. The vertex set
    stays the same, so vertex numbers match between the two graphs.
    """
    nodes = pl.read_parquet(GRAPH_NODES).sort("node")
    edges = pl.read_parquet(EDGES)
    if not with_merges:
        edges = edges.filter(pl.col("relation") != "merge")

    index = dict(zip(nodes["_id"], nodes["node"]))
    pairs = [(index[c], index[p]) for c, p in zip(edges["child_id"], edges["parent_id"])]

    g = ig.Graph(n=nodes.height, edges=pairs, directed=True)
    g.vs["name"] = nodes["name"].to_list()
    g.vs["family"] = nodes["family"].to_list()
    g.es["relation"] = edges["relation"].to_list()
    return g, nodes


if __name__ == "__main__":
    for flag in (True, False):
        g, nodes = load_graph(with_merges=flag)
        label = "G_full" if flag else "G_nomerge"
        sizes = sorted(g.connected_components(mode="weak").sizes(), reverse=True)
        print(
            f"{label}: {g.vcount():,} vertices, {g.ecount():,} edges, "
            f"DAG: {g.is_dag()}, weak components: {len(sizes):,}, largest: {sizes[0]:,}"
        )
