"""RQ4: how many models would inherit a flaw in a base model, and how much do
merges add?

The data has no flaw labels. RQ4 therefore asks a hypothetical question: if a
model had a flaw (a licence problem, a backdoor, a safety issue), which models
could have inherited it? The assumption is that a model inherits fully from
every parent, including every parent of a merge. That is reasonable for
licences and weaker for learned behaviour.

Measures
    1. reach(v) = number of descendants of v, by BFS against the edge
       direction (own code; Topic 5), on G_full and on G_nomerge
    2. reach of every root, with and without merges: distribution, largest,
       and the reach that merges add
    3. models exposed to more than one root (only possible through merges)
    4. audit coverage: if the top-k models are audited, what share of all
       models is audited or descends from an audited model? Hubs against
       random models (random failure versus hub failure, Topic 4)

Output
    data/processed/rq4_*.csv, rq4_summary.json
    figures/rq4_*.png

Run from the project root, after build_graph.py:

    python src/rq4.py
"""

import json
from collections import deque

import numpy as np
import polars as pl
import matplotlib.pyplot as plt

from graph_io import load_graph
from pagerank_dag import pagerank_on_dag
from plotstyle import INK_SECONDARY, MUTED, SERIES, apply_style, save

OUT = "data/processed"
SEED = 6917
RANDOM_DRAWS = 20
K_VALUES = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000]
TOP = 20
summary = {}

apply_style()
g_full, nodes = load_graph(with_merges=True)
g_nomerge, _ = load_graph(with_merges=False)
n = g_full.vcount()
name = nodes["name"].to_list()
family = nodes["family"].to_list()
is_root = np.array(nodes["is_root"].to_list())
n_roots = np.array(nodes["n_roots"].to_list())
depth = np.array(nodes["depth"].to_list())
print(f"graph: {n:,} models, {is_root.sum():,} roots")


# ---------------------------------------------------------------------------
# 1. Reach of every model
# ---------------------------------------------------------------------------
def descendants(v, children_of):
    """BFS from v against the edge direction. Returns the set of descendants."""
    seen = {v}
    queue = deque([v])
    while queue:
        x = queue.popleft()
        for c in children_of[x]:
            if c not in seen:
                seen.add(c)
                queue.append(c)
    seen.discard(v)
    return seen


def all_reach(graph):
    """reach[v] = number of descendants, for every model."""
    children_of = graph.get_adjlist(mode="in")        # edges are child -> parent
    reach = np.zeros(graph.vcount(), dtype=np.int64)
    for v in range(graph.vcount()):
        if children_of[v]:
            reach[v] = len(descendants(v, children_of))
    return reach, children_of


reach_full, children_full = all_reach(g_full)
reach_nomerge, children_nomerge = all_reach(g_nomerge)

# Check: the number of descendants of every root, summed, must equal the
# number of (root, descendant) pairs, which is the sum of n_roots over non-roots.
assert reach_full[is_root].sum() == n_roots[~is_root].sum(), "reach does not match the root sets"
print("check: root reach agrees with the root sets from build_graph.py")

pl.DataFrame({
    "node": list(range(n)), "name": name, "family": family, "is_root": is_root,
    "reach_full": reach_full, "reach_nomerge": reach_nomerge,
}).write_parquet(f"{OUT}/rq4_reach.parquet")


# ---------------------------------------------------------------------------
# 2. Reach of the roots, with and without merges
# ---------------------------------------------------------------------------
roots = np.flatnonzero(is_root)
rf, rn = reach_full[roots], reach_nomerge[roots]
added = rf - rn
summary["root_reach"] = {
    "roots": int(len(roots)),
    "total_with_merges": int(rf.sum()),
    "total_without_merges": int(rn.sum()),
    "added_by_merges": int(added.sum()),
    "added_share": float(added.sum() / rn.sum()),
    "largest_with_merges": int(rf.max()),
    "largest_without_merges": int(rn.max()),
    "roots_that_gain": int((added > 0).sum()),
    "median_reach_with_merges": float(np.median(rf)),
    "roots_reach_1000plus_with": int((rf >= 1000).sum()),
    "roots_reach_1000plus_without": int((rn >= 1000).sum()),
}
s = summary["root_reach"]
print(f"\n[2] reach of the {len(roots):,} roots")
print(f"    total (root, descendant) pairs: {s['total_without_merges']:,} without merges, "
      f"{s['total_with_merges']:,} with merges (+{100 * s['added_share']:.1f}%)")
print(f"    largest reach: {s['largest_without_merges']:,} without, {s['largest_with_merges']:,} with")
print(f"    roots that gain descendants through merges: {s['roots_that_gain']:,} of {len(roots):,}")
print(f"    roots with 1,000+ descendants: {s['roots_reach_1000plus_without']} without, "
      f"{s['roots_reach_1000plus_with']} with")

order = roots[np.argsort(-reach_full[roots], kind="stable")]
top_roots = pl.DataFrame({
    "rank": list(range(1, TOP + 1)),
    "root": [name[v] for v in order[:TOP]],
    "family": [family[v] for v in order[:TOP]],
    "reach_without_merges": [int(reach_nomerge[v]) for v in order[:TOP]],
    "reach_with_merges": [int(reach_full[v]) for v in order[:TOP]],
    "added_by_merges": [int(reach_full[v] - reach_nomerge[v]) for v in order[:TOP]],
    "added_percent": [100 * (reach_full[v] - reach_nomerge[v]) / max(reach_nomerge[v], 1) for v in order[:TOP]],
})
top_roots.write_csv(f"{OUT}/rq4_top_roots.csv")
print(f"\n    top {TOP} roots by reach:")
for row in top_roots.iter_rows(named=True):
    print(f"      {row['rank']:>2}  {row['reach_without_merges']:>7,} -> {row['reach_with_merges']:>7,}  "
          f"(+{row['added_percent']:>5.1f}%)  {row['root']}  [{row['family']}]")

# Largest relative gains among roots that already reach 1,000 models.
big = roots[reach_nomerge[roots] >= 1000]
gain = (reach_full[big] - reach_nomerge[big]) / reach_nomerge[big]
print("    largest relative gains among roots with 1,000+ descendants:")
for v, x in sorted(zip(big, gain), key=lambda t: -t[1])[:8]:
    print(f"      +{100 * x:>6.1f}%  {reach_nomerge[v]:>6,} -> {reach_full[v]:>6,}  {name[v]}")
summary["largest_relative_gains_1000plus"] = [
    {"root": name[v], "without": int(reach_nomerge[v]), "with": int(reach_full[v]), "gain": float(x)}
    for v, x in sorted(zip(big, gain), key=lambda t: -t[1])[:10]
]

# Figure: distribution of root reach.
fig, ax = plt.subplots(figsize=(4.2, 3.2))
for values, label, colour in ((rf, "with merges", SERIES[0]), (rn, "without merges", SERIES[1])):
    v = values[values >= 1]
    k, counts = np.unique(v, return_counts=True)
    p = np.cumsum(counts[::-1])[::-1] / len(roots)
    ax.loglog(k, p, color=colour, label=label)
ax.set(title="Descendants per root model", xlabel="descendants r", ylabel="share of roots with reach >= r")
ax.legend(loc="lower left")
save(fig, "rq4_root_reach")

# Figure: top 15 roots, reach without merges plus what merges add.
fig, ax = plt.subplots(figsize=(5.6, 4.0))
shown = top_roots.head(15).reverse()
y = np.arange(shown.height)
ax.barh(y, shown["reach_without_merges"], color=SERIES[1], height=0.65, label="without merges")
ax.barh(y, shown["added_by_merges"], left=shown["reach_without_merges"], color=SERIES[0], height=0.65,
        label="added by merges")
ax.set_yticks(y, [r.split("/")[-1][:30] for r in shown["root"]], fontsize=7)
ax.xaxis.set_major_formatter(lambda value, _: f"{value:,.0f}")
ax.set(title="Top 15 roots by descendants", xlabel="descendants")
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right")
save(fig, "rq4_top_roots")


# ---------------------------------------------------------------------------
# 3. Models exposed to more than one root
# ---------------------------------------------------------------------------
non_root = ~is_root
multi = non_root & (n_roots >= 2)
mixed = np.array([f == "mixed" for f in family])
summary["multi_root_exposure"] = {
    "non_root_models": int(non_root.sum()),
    "models_with_2plus_roots": int(multi.sum()),
    "share_of_non_root": float(multi.sum() / non_root.sum()),
    "max_roots_of_one_model": int(n_roots.max()),
    "models_with_10plus_roots": int((n_roots >= 10).sum()),
    "models_with_2plus_named_families": int(mixed.sum()),
}
m = summary["multi_root_exposure"]
print(f"\n[3] models that descend from 2 or more roots: {m['models_with_2plus_roots']:,} "
      f"({100 * m['share_of_non_root']:.2f}% of non-root models)")
print(f"    most roots behind one model: {m['max_roots_of_one_model']}; "
      f"models with 10+ roots: {m['models_with_10plus_roots']:,}")
print(f"    models whose roots span 2+ named families: {m['models_with_2plus_named_families']:,}")


# ---------------------------------------------------------------------------
# 4. Audit coverage: hubs against random models
# ---------------------------------------------------------------------------
def coverage_curve(ranking, children_of):
    """Share of all models that are audited or descend from an audited model,
    when the first k models of `ranking` are audited, for each k in K_VALUES."""
    covered = np.zeros(n, dtype=bool)
    curve = []
    k_done = 0
    for k in K_VALUES:
        for v in ranking[k_done:k]:
            covered[v] = True
            for d in descendants(v, children_of):
                covered[d] = True
        k_done = k
        curve.append(covered.sum() / n)
    return curve


pagerank = pagerank_on_dag(g_full, depth, 0.85, 1.0)
in_degree = np.array(g_full.degree(mode="in"))
rankings = {
    "by children": np.argsort(-in_degree, kind="stable"),
    "by PageRank": np.argsort(-pagerank, kind="stable"),
    "by reach": np.argsort(-reach_full, kind="stable"),
}
curves = {label: coverage_curve(r, children_full) for label, r in rankings.items()}
# The same "by reach" strategy on the graph without merges: how much do merges
# change what an audit of the top models covers?
curves["by reach, without merges"] = coverage_curve(np.argsort(-reach_nomerge, kind="stable"), children_nomerge)

rng = np.random.default_rng(SEED)
with_children = np.flatnonzero(in_degree >= 1)
random_all = np.mean([coverage_curve(rng.permutation(n), children_full) for _ in range(RANDOM_DRAWS)], axis=0)
random_parents = np.mean([coverage_curve(rng.permutation(with_children), children_full)
                          for _ in range(RANDOM_DRAWS)], axis=0)
curves["random models"] = list(random_all)
curves["random models with a child"] = list(random_parents)

pl.DataFrame({"k": K_VALUES, **{label: values for label, values in curves.items()}}
             ).write_csv(f"{OUT}/rq4_audit_coverage.csv")
summary["audit_coverage"] = {label: dict(zip(map(str, K_VALUES), map(float, values)))
                             for label, values in curves.items()}

print(f"\n[4] audit coverage: share of all {n:,} models audited or descending from an audited model")
print(f"    {'k':>6}" + "".join(f"{label[:22]:>24}" for label in curves))
for i, k in enumerate(K_VALUES):
    print(f"    {k:>6}" + "".join(f"{100 * curves[label][i]:>23.2f}%" for label in curves))

fig, ax = plt.subplots(figsize=(4.8, 3.4))
styles = {
    "by reach": (SERIES[0], "-"),
    "by PageRank": (SERIES[2], "-"),
    "by children": (SERIES[3], "-"),
    "by reach, without merges": (SERIES[1], "--"),
    "random models with a child": (MUTED, ":"),
}
for label, (colour, line) in styles.items():
    ax.semilogx(K_VALUES, [100 * v for v in curves[label]], line, color=colour, label=label, marker="o",
                markersize=3)
ax.set(title="Models covered by auditing the top k", xlabel="models audited, k",
       ylabel="% of models covered", ylim=(0, 100))
ax.legend(loc="upper left", fontsize=7)
save(fig, "rq4_audit_coverage")
print(f"    (random models from all {n:,}: {100 * random_all[-1]:.2f}% covered at k = {K_VALUES[-1]}, "
      f"not drawn in the figure)")

with open(f"{OUT}/rq4_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"\nsaved {OUT}/rq4_summary.json")
