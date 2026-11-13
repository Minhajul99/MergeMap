"""PageRank by matrix inverse, exactly as in the lecture notes (Topic 3).

This is the pagerank() function from Assignment 3, unchanged. It builds the
full n x n matrix, so it only works for small graphs (about 1,000 vertices).
rq3.py uses it to check the fast PageRank on a small piece of the graph.

    x = D (D - a A)^-1 b 1

    A[i][j] = 1 if there is an edge from j to i
    D       = diagonal matrix of out-degrees, with 0 replaced by 1
"""

from numpy.linalg import inv


def pagerank(edges, a, b):
    """Return (first_index, x), where x[k] is the PageRank of vertex first_index + k."""
    first = 0 if any(x == 0 or y == 0 for x, y in edges) else 1
    last = max(max(x, y) for x, y in edges)
    n = last - first + 1

    A = [[0.0] * n for _ in range(n)]
    out_degree = [0] * n
    for x, y in edges:
        A[y - first][x - first] = 1.0
        out_degree[x - first] += 1

    D = [max(d, 1) for d in out_degree]

    M = [[-a * A[i][j] for j in range(n)] for i in range(n)]
    for i in range(n):
        M[i][i] += D[i]

    M_inv = inv(M).tolist()
    x = [b * D[i] * sum(M_inv[i]) for i in range(n)]
    return first, x
