"""RQ3: which models act as hubs or bridges?

Measures
    1. hubs: in-degree (children) and PageRank on the child -> parent graph
       (Topic 3). PageRank is computed with own code and checked twice:
       against the Assignment 3 matrix-inverse code on a small component, and
       against igraph on the whole graph.
    2. bridges in the lineage graph: betweenness on directed paths (Topic 5)
    3. bridges between merge parents: betweenness on the cocitation network
    4. communities of the cocitation network (modularity maximisation,
       Topic 5-3) compared with the family labels

Note on eigenvector centrality: it is not used. In an acyclic directed graph
every vertex gets eigenvector centrality zero (Topic 3), so PageRank, which
gives every vertex a small amount for free, is the right choice here.

Output
    data/processed/rq3_*.csv, rq3_summary.json
    figures/rq3_*.png

Run from the project root, after rq2.py:

    python src/rq3.py
"""

import json
from collections import Counter

import igraph as ig
import leidenalg
import numpy as np
import polars as pl
import matplotlib.pyplot as plt

from graph_io import load_graph
from pagerank_matrix import pagerank as pagerank_by_inverse
from plotstyle import INK_SECONDARY, SERIES, apply_style, save

OUT = "data/processed"
ALPHA = 0.85        # share of a model's score passed on to its parents
BETA = 1.0          # score every model gets for free
SEED = 6917
TOP = 20
summary = {}

apply_style()
g, nodes = load_graph(with_merges=True)
n = g.vcount()
name = nodes["name"].to_list()
family = nodes["family"].to_list()
relation = nodes["relation"].to_list()
depth = np.array(nodes["depth"].to_list())
is_merge = np.array([r == "merge" for r in relation])
children = np.array(g.degree(mode="in"))
n_parents = np.array(g.degree(mode="out"))
print(f"G_full: {n:,} nodes, {g.ecount():,} edges")


# ---------------------------------------------------------------------------
# 1. Hubs: children and PageRank
# ---------------------------------------------------------------------------
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


pr = pagerank_on_dag(g, depth, ALPHA, BETA)

# Check 1: the Assignment 3 code on one small component that contains merges.
components = g.connected_components(mode="weak")
candidates = [c for c in components
              if 200 <= len(c) <= 1000 and is_merge[c].any()]
piece = max(candidates, key=len)
local = {v: i + 1 for i, v in enumerate(piece)}                  # vertex numbers 1 .. n
piece_edges = {(local[e.source], local[e.target]) for e in g.es.select(_within=piece)}
_, by_inverse = pagerank_by_inverse(piece_edges, ALPHA, BETA)
largest_gap = max(abs(by_inverse[local[v] - 1] - pr[v]) for v in piece)
print(f"\n[1] PageRank check 1: Assignment 3 matrix inverse on a component of {len(piece)} models, "
      f"{len(piece_edges)} edges: largest difference {largest_gap:.2e}")

# Check 2: igraph on the whole graph. igraph rescales the scores to sum to 1,
# so the two results should differ only by one constant factor.
pr_igraph = np.array(g.pagerank(damping=ALPHA))
ratio = pr / pr_igraph
print(f"    PageRank check 2: igraph on the whole graph: own / igraph ratio is constant to "
      f"{(ratio.max() - ratio.min()) / ratio.mean():.2e} (relative spread)")
summary["pagerank_checks"] = {
    "alpha": ALPHA, "beta": BETA,
    "matrix_inverse_component_size": len(piece),
    "matrix_inverse_largest_difference": float(largest_gap),
    "igraph_ratio_relative_spread": float((ratio.max() - ratio.min()) / ratio.mean()),
}


def top_table(score, label, k=TOP):
    order = np.argsort(-score)[:k]
    return pl.DataFrame({
        "rank": list(range(1, k + 1)),
        "model": [name[v] for v in order],
        label: [float(score[v]) for v in order],
        "children": [int(children[v]) for v in order],
        "family": [family[v] for v in order],
        "relation": [relation[v] or "root" for v in order],
        "depth": [int(depth[v]) for v in order],
    })


top_children = top_table(children.astype(float), "children_score").drop("children_score")
top_pagerank = top_table(pr, "pagerank")
top_children.write_csv(f"{OUT}/rq3_top_children.csv")
top_pagerank.write_csv(f"{OUT}/rq3_top_pagerank.csv")

print(f"\n    top {TOP} by children (in-degree):")
for row in top_children.iter_rows(named=True):
    print(f"      {row['rank']:>2}  {row['children']:>6,}  {row['model']}  [{row['family']}]")
print(f"\n    top {TOP} by PageRank:")
for row in top_pagerank.iter_rows(named=True):
    print(f"      {row['rank']:>2}  {row['pagerank']:>9,.0f}  children {row['children']:>6,}  "
          f"{row['model']}  [{row['family']}]")

top_c = set(np.argsort(-children)[:TOP])
top_p = set(np.argsort(-pr)[:TOP])
has_children = children >= 1
rank_children = np.argsort(np.argsort(-children[has_children]))
rank_pagerank = np.argsort(np.argsort(-pr[has_children]))
spearman = float(np.corrcoef(rank_children, rank_pagerank)[0, 1])
family_in_top_pr = Counter(family[v] for v in np.argsort(-pr)[:100])
summary["hubs"] = {
    "overlap_top20_children_pagerank": len(top_c & top_p),
    "spearman_children_pagerank_among_parents": spearman,
    "roots_in_top20_pagerank": int(sum(1 for v in top_p if n_parents[v] == 0)),
    "families_in_top100_pagerank": family_in_top_pr.most_common(),
    "pagerank_share_top20": float(np.sort(pr - BETA)[::-1][:TOP].sum() / (pr - BETA).sum()),
}
print(f"\n    overlap of the two top-{TOP} lists: {len(top_c & top_p)} models")
print(f"    rank correlation (Spearman) of children and PageRank, models with children: {spearman:.3f}")
print(f"    top-{TOP} PageRank models hold {100 * summary['hubs']['pagerank_share_top20']:.1f}% "
      f"of all passed-on score")
print(f"    families in the top 100 by PageRank: "
      f"{', '.join(f'{f} {c}' for f, c in family_in_top_pr.most_common(8))}")

# Figure: PageRank against children. Models above the cloud gain score from
# descendants further down, not from their own children.
fig, ax = plt.subplots(figsize=(4.6, 3.6))
ax.loglog(children[has_children], pr[has_children], "o", color=SERIES[0], markersize=2, alpha=0.25,
          markeredgewidth=0)
# Label two models: the top one, and the top one whose score is at least three
# times its own number of children (its score comes from further down).
top_model = int(np.argmax(pr))
lifted = np.where(pr >= 3 * children, pr, 0)
lifted_model = int(np.argmax(lifted))
for v in (top_model, lifted_model):
    ax.annotate(name[v].split("/")[-1], (children[v], pr[v]), textcoords="offset points",
                xytext=(-6, 3), ha="right", fontsize=7, color=INK_SECONDARY)
ax.set(title="PageRank against number of children", xlabel="children (in-degree)",
       ylabel=f"PageRank (alpha = {ALPHA})")
save(fig, "rq3_pagerank_vs_children")


# ---------------------------------------------------------------------------
# 2. Bridges in the lineage graph: betweenness on directed paths
# ---------------------------------------------------------------------------
# A directed path runs from a model up to one of its ancestors. A model has
# high betweenness when many descendant-to-ancestor shortest paths pass
# through it: it has many descendants below it AND ancestors above it.
# Paths only go upwards and stop at a root, so the exact value is cheap.
between = np.array(g.betweenness(directed=True))
positive = between > 0
order_b = np.argsort(-between)
top_between = pl.DataFrame({
    "rank": list(range(1, TOP + 1)),
    "model": [name[v] for v in order_b[:TOP]],
    "betweenness": [float(between[v]) for v in order_b[:TOP]],
    "children": [int(children[v]) for v in order_b[:TOP]],
    "parents": [int(n_parents[v]) for v in order_b[:TOP]],
    "family": [family[v] for v in order_b[:TOP]],
    "relation": [relation[v] or "root" for v in order_b[:TOP]],
})
top_between.write_csv(f"{OUT}/rq3_top_betweenness.csv")

merge_share_all = float(is_merge.mean())
merge_share_positive = float(is_merge[positive].mean())
merge_share_top = {k: float(is_merge[order_b[:k]].mean()) for k in (20, 100, 1000)}
betweenness_held_by_merges = float(between[is_merge].sum() / between.sum())
summary["lineage_betweenness"] = {
    "nodes_with_positive_betweenness": int(positive.sum()),
    "merge_share_of_all_nodes": merge_share_all,
    "merge_share_of_positive": merge_share_positive,
    "merge_share_of_top": merge_share_top,
    "share_of_total_betweenness_held_by_merges": betweenness_held_by_merges,
}
print(f"\n[2] lineage betweenness (directed paths): {positive.sum():,} models are on at least one path")
print(f"    merges are {100 * merge_share_all:.1f}% of all models, "
      f"{100 * merge_share_positive:.1f}% of models with betweenness > 0,")
print(f"    {100 * merge_share_top[1000]:.1f}% of the top 1,000, {100 * merge_share_top[100]:.1f}% of the top 100, "
      f"{100 * merge_share_top[20]:.1f}% of the top 20")
print(f"    merges hold {100 * betweenness_held_by_merges:.1f}% of all betweenness")
print(f"    top {TOP}:")
for row in top_between.iter_rows(named=True):
    print(f"      {row['rank']:>2}  {row['betweenness']:>10,.0f}  {row['relation']:<9} "
          f"children {row['children']:>5,}  parents {row['parents']:>2}  {row['model']}  [{row['family']}]")

fig, ax = plt.subplots(figsize=(5.6, 4.0))
shown = top_between.head(15).reverse()
colours = [SERIES[1] if r == "merge" else SERIES[0] for r in shown["relation"]]
ax.barh(range(shown.height), shown["betweenness"], color=colours, height=0.65)
ax.set_yticks(range(shown.height), [m.split("/")[-1][:34] for m in shown["model"]], fontsize=7)
ax.set(title="Top 15 models by lineage betweenness", xlabel="betweenness (directed shortest paths)")
ax.grid(axis="y", visible=False)
ax.xaxis.set_major_formatter(lambda value, _: f"{value:,.0f}")
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=SERIES[1]), plt.Rectangle((0, 0), 1, 1, color=SERIES[0])],
          labels=["merge", "not a merge"], loc="lower right")
save(fig, "rq3_lineage_betweenness")


# ---------------------------------------------------------------------------
# 3. Bridges between merge parents: betweenness on the cocitation network
# ---------------------------------------------------------------------------
cocitation = pl.read_parquet(f"{OUT}/cocitation_edges.parquet")
index_of = {m: i for i, m in enumerate(name)}
members = sorted({index_of[x] for x in cocitation["a"]} | {index_of[x] for x in cocitation["b"]})
position = {v: i for i, v in enumerate(members)}
cg = ig.Graph(
    n=len(members),
    edges=[(position[index_of[a]], position[index_of[b]]) for a, b in zip(cocitation["a"], cocitation["b"])],
    directed=False,
)
cg.es["weight"] = cocitation["weight"].to_list()
c_family = [family[v] for v in members]

c_between = np.array(cg.betweenness())           # exact, unweighted shortest paths
c_degree = np.array(cg.degree())
c_strength = np.array(cg.strength(weights="weight"))
order_cb = np.argsort(-c_between)


def neighbour_families(i):
    """Named families among the cocitation neighbours of vertex i."""
    return sorted({c_family[j] for j in cg.neighbors(i)} - {"unknown", "mixed"})


top_cocitation = pl.DataFrame({
    "rank": list(range(1, TOP + 1)),
    "model": [name[members[i]] for i in order_cb[:TOP]],
    "betweenness": [float(c_between[i]) for i in order_cb[:TOP]],
    "cocited_with": [int(c_degree[i]) for i in order_cb[:TOP]],
    "merges_weight": [int(c_strength[i]) for i in order_cb[:TOP]],
    "family": [c_family[i] for i in order_cb[:TOP]],
    "neighbour_families": [", ".join(neighbour_families(i)) for i in order_cb[:TOP]],
})
top_cocitation.write_csv(f"{OUT}/rq3_top_cocitation_betweenness.csv")
multi_family_bridges = sum(1 for i in order_cb[:100] if len(neighbour_families(i)) >= 2)
summary["cocitation_betweenness"] = {
    "nodes": cg.vcount(), "edges": cg.ecount(),
    "top100_with_neighbours_in_2plus_families": multi_family_bridges,
    "families_of_top100": Counter(c_family[i] for i in order_cb[:100]).most_common(),
}
print(f"\n[3] cocitation betweenness: top {TOP} of {cg.vcount():,} merge parents")
for row in top_cocitation.iter_rows(named=True):
    print(f"      {row['rank']:>2}  {row['betweenness']:>10,.0f}  cocited with {row['cocited_with']:>4}  "
          f"{row['model']}  [{row['family']}]  neighbours: {row['neighbour_families']}")
print(f"    of the top 100, {multi_family_bridges} have cocitation neighbours in 2 or more named families")


# ---------------------------------------------------------------------------
# 4. Communities of the cocitation network versus family labels
# ---------------------------------------------------------------------------
partition = leidenalg.find_partition(cg, leidenalg.ModularityVertexPartition, weights="weight", seed=SEED)
community = np.array(partition.membership)
q_leiden = cg.modularity(community, weights="weight")
label_ids = {f: i for i, f in enumerate(sorted(set(c_family)))}
q_family = cg.modularity([label_ids[f] for f in c_family], weights="weight")

rows = []
pure_named = total_named = 0
unknown_total = unknown_in_clear = 0
for c in range(len(partition)):
    inside = np.flatnonzero(community == c)
    labels = Counter(c_family[i] for i in inside)
    named = Counter({f: k for f, k in labels.items() if f not in ("unknown", "mixed")})
    named_total = sum(named.values())
    dominant, dominant_count = named.most_common(1)[0] if named else ("-", 0)
    purity = dominant_count / named_total if named_total else float("nan")
    total_named += named_total
    pure_named += dominant_count
    unknown_total += labels["unknown"]
    # A community is "clear" if it has at least 10 named members and 90% of them agree.
    if named_total >= 10 and purity >= 0.9:
        unknown_in_clear += labels["unknown"]
    rows.append({
        "community": c, "size": len(inside), "dominant_family": dominant,
        "purity_among_named": purity, "named": named_total,
        "unknown": labels["unknown"], "mixed": labels["mixed"],
    })
table = pl.DataFrame(rows).sort("size", descending=True)
table.write_csv(f"{OUT}/rq3_communities.csv")

summary["communities"] = {
    "communities": len(partition),
    "communities_with_10plus_members": int((table["size"] >= 10).sum()),
    "modularity_leiden": float(q_leiden),
    "modularity_family_labels": float(q_family),
    "overall_purity_among_named": pure_named / total_named,
    "unknown_parents": unknown_total,
    "unknown_parents_in_clear_communities": unknown_in_clear,
}
print(f"\n[4] Leiden communities on the cocitation network: {len(partition):,} "
      f"({(table['size'] >= 10).sum()} with 10+ members)")
print(f"    modularity Q: Leiden {q_leiden:.3f}, family labels {q_family:.3f}")
print(f"    named parents that sit in their community's dominant family: "
      f"{100 * pure_named / total_named:.1f}%")
print(f"    unknown parents inside a clearly single-family community: {unknown_in_clear:,} of {unknown_total:,} "
      f"({100 * unknown_in_clear / unknown_total:.1f}%)")
print("    largest communities:")
print(f"      {'size':>6}  {'dominant':<10}{'purity':>7}{'named':>7}{'unknown':>9}{'mixed':>7}")
for row in table.head(12).iter_rows(named=True):
    print(f"      {row['size']:>6,}  {row['dominant_family']:<10}{100 * row['purity_among_named']:>6.1f}%"
          f"{row['named']:>7,}{row['unknown']:>9,}{row['mixed']:>7,}")

with open(f"{OUT}/rq3_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"\nsaved {OUT}/rq3_summary.json")
