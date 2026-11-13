"""Phase 2: build the lineage graph from the cleaned edge list.

Graph model
    node  = a model that appears in at least one edge
    edge  = child -> parent ("derived from"), labelled by the child's relation

What this script computes for every node
    * a topological order and a cycle check (own code, Kahn's algorithm,
      adapted from Assignment 2)
    * lineage depth: the longest path from the node to a root
    * its roots: the models with no declared parent that it descends from
    * its family: from the names of its roots (see families.py)

Output
    data/processed/graph_nodes.parquet   one row per node

Run from the project root, after build_edges.py:

    python src/build_graph.py
"""

from collections import Counter, deque

import polars as pl

from families import MIXED, UNKNOWN, family_of_root

EDGES = "data/processed/edges.parquet"
NODES = "data/processed/nodes.parquet"
OUT = "data/processed/graph_nodes.parquet"


# ---------------------------------------------------------------------------
# 1. Load edges and give every node an integer index 0 .. n-1
# ---------------------------------------------------------------------------
edges = pl.read_parquet(EDGES)

all_ids = pl.concat([edges["child_id"], edges["parent_id"]]).unique(maintain_order=True)
ids = all_ids.to_list()
index = {model_id: i for i, model_id in enumerate(ids)}
n = len(ids)

child = [index[x] for x in edges["child_id"]]
parent = [index[x] for x in edges["parent_id"]]
m = len(child)
print(f"nodes: {n:,}   edges: {m:,}")

# Adjacency lists. Edge direction is child -> parent, so:
#   parents_of[v]  = out-neighbours of v
#   children_of[v] = in-neighbours of v
parents_of = [[] for _ in range(n)]
children_of = [[] for _ in range(n)]
for c, p in zip(child, parent):
    parents_of[c].append(p)
    children_of[p].append(c)


# ---------------------------------------------------------------------------
# 2. Topological sort (Kahn's algorithm) -- also the cycle check
# ---------------------------------------------------------------------------
def topological_sort(n, out_neighbours, in_neighbours):
    """Return a topological order, or None if the graph has a cycle.

    Start with every vertex that has no incoming edge, remove it, and free
    any vertex whose incoming edges are now all gone. If some vertices are
    never freed, they lie on a cycle.
    """
    in_degree = [len(in_neighbours[v]) for v in range(n)]
    queue = deque(v for v in range(n) if in_degree[v] == 0)
    order = []
    while queue:
        u = queue.popleft()
        order.append(u)
        for w in out_neighbours[u]:
            in_degree[w] -= 1
            if in_degree[w] == 0:
                queue.append(w)
    if len(order) < n:
        return None
    return order


order = topological_sort(n, parents_of, children_of)
if order is None:
    raise SystemExit("The graph has a cycle. Fix the cleaning rules in build_edges.py.")
print("cycle check: no cycles, the graph is a DAG")

# In this order every child comes before its parents. Reversed, every parent
# comes before its children, which is the order needed below.
parents_first = order[::-1]


# ---------------------------------------------------------------------------
# 3. Lineage depth and root sets, in one pass from the roots downwards
# ---------------------------------------------------------------------------
depth = [0] * n          # longest path from the node up to a root
roots_of = [None] * n    # frozenset of root indices

for v in parents_first:
    ps = parents_of[v]
    if not ps:                       # no parents: v is a root
        roots_of[v] = frozenset([v])
    elif len(ps) == 1:               # one parent: same roots, one step deeper
        roots_of[v] = roots_of[ps[0]]
        depth[v] = depth[ps[0]] + 1
    else:                            # several parents (only merges)
        combined = set()
        for p in ps:
            combined |= roots_of[p]
        roots_of[v] = frozenset(combined)
        depth[v] = 1 + max(depth[p] for p in ps)

is_root = [not parents_of[v] for v in range(n)]
print(f"roots: {sum(is_root):,}   deepest lineage: {max(depth)} generations")


# ---------------------------------------------------------------------------
# 4. Names, then family labels
# ---------------------------------------------------------------------------
node_info = pl.read_parquet(NODES)
name_of = dict(zip(node_info["_id"], node_info["id"]))
# Ghost parents are not in the node table; their name comes from the edge list.
for pid, pname in edges.filter("ghost").select("parent_id", "parent_name").iter_rows():
    name_of.setdefault(pid, pname)

names = [name_of.get(model_id) or model_id for model_id in ids]

root_family = {v: family_of_root(names[v]) for v in range(n) if is_root[v]}


def families_of(v):
    """Named families among the roots of v. 'unknown' roots are left out."""
    return sorted({root_family[r] for r in roots_of[v]} - {UNKNOWN})


def family_label(named):
    """One label per node: a family name, 'mixed' or 'unknown'."""
    if not named:
        return UNKNOWN
    if len(named) == 1:
        return named[0]
    return MIXED


families = [families_of(v) for v in range(n)]
family = [family_label(f) for f in families]
# True if at least one root of the node has no recognisable family.
has_unknown_root = [any(root_family[r] == UNKNOWN for r in roots_of[v]) for v in range(n)]


# ---------------------------------------------------------------------------
# 5. Save one row per node
# ---------------------------------------------------------------------------
relation_of = dict(zip(edges["child_id"], edges["relation"]))
ghost_ids = set(edges.filter("ghost")["parent_id"])

table = pl.DataFrame(
    {
        "node": list(range(n)),
        "_id": ids,
        "name": names,
        "ghost": [model_id in ghost_ids for model_id in ids],
        "relation": [relation_of.get(model_id) for model_id in ids],   # null for roots
        "n_parents": [len(parents_of[v]) for v in range(n)],
        "n_children": [len(children_of[v]) for v in range(n)],
        "is_root": is_root,
        "depth": depth,
        "n_roots": [len(roots_of[v]) for v in range(n)],
        "roots": [sorted(roots_of[v]) for v in range(n)],              # node indices
        "families": families,
        "family": family,
        "has_unknown_root": has_unknown_root,
    },
    schema_overrides={"roots": pl.List(pl.Int32), "families": pl.List(pl.String)},
).join(
    node_info.select("_id", "author", "createdAt", "downloads", "likes"), on="_id", how="left"
).sort("node")      # a join does not promise to keep row order
table.write_parquet(OUT)
print(f"saved {OUT}")


# ---------------------------------------------------------------------------
# 6. Summary: how well do the family labels cover the graph?
# ---------------------------------------------------------------------------
def share(part, whole):
    return f"{100 * part / whole:.1f}%"


n_roots = sum(is_root)
unknown_roots = sum(1 for v in root_family if root_family[v] == UNKNOWN)
print()
print(f"roots with a named family: {n_roots - unknown_roots:,} of {n_roots:,} "
      f"({share(n_roots - unknown_roots, n_roots)})")

non_roots = [v for v in range(n) if not is_root[v]]
label_counts = Counter(family[v] for v in non_roots)
print(f"non-root models by label ({len(non_roots):,} in total):")
for label, count in label_counts.most_common(15):
    print(f"  {label:<18}{count:>9,}  {share(count, len(non_roots))}")

merge_children = [v for v in range(n) if relation_of.get(ids[v]) == "merge" and len(parents_of[v]) >= 2]
merge_parents = {p for v in merge_children for p in parents_of[v]}
unknown_parents = sum(1 for p in merge_parents if family[p] == UNKNOWN)
print(f"merges with 2+ parents: {len(merge_children):,}")
print(f"distinct merge parents: {len(merge_parents):,}, labelled unknown: "
      f"{unknown_parents:,} ({share(unknown_parents, len(merge_parents))})")

# The largest roots that the pattern list does not recognise.
reach = Counter()
for v in non_roots:
    for r in roots_of[v]:
        reach[r] += 1
unknown_by_reach = sorted(
    (r for r in root_family if root_family[r] == UNKNOWN), key=lambda r: -reach[r]
)
print("largest unknown roots:")
for r in unknown_by_reach[:25]:
    print(f"  {reach[r]:>6,}  {names[r]}")
