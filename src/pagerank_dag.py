"""PageRank on the lineage graph, solved exactly in one pass (Topic 3).

Used by rq3.py (hubs) and rq4.py (audit coverage).
"""

import numpy as np


def pagerank_on_dag(graph, depth, alpha, beta):
    """PageRank x = alpha * A D^-1 x + beta * 1, solved exactly in one pass.

    A model passes the share alpha of its score to its parents, split equally
    among them. The graph is acyclic, so if every child is handled before its
    parents, each score is final when it is passed on. Children always have a
    larger depth than their parents, so "deepest first" is such an order.
    """
    x = np.full(graph.vcount(), beta, dtype=float)
    parents = graph.get_adjlist(mode="out")
    for v in np.argsort(-depth, kind="stable"):
        ps = parents[v]
        if ps:
            share = alpha * x[v] / len(ps)
            for p in ps:
                x[p] += share
    return x
