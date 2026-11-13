"""RQ1: how much do merges connect separate model families?

Measures (all from the lectures, Topic 2 and Topic 4):
    1. distribution of children per model: log-binned histogram, cumulative
       distribution, power-law exponent from the cumulative slope
    2. top-heavy share: share of all edges held by the top P% of models
    3. parents per merge
    4. weakly connected components, with and without merge edges
    5. lineage depth, with and without merge edges
    6. share of merges whose parents come from different roots / families

Output
    data/processed/rq1_*.csv and rq1_summary.json
    figures/rq1_*.png

Run from the project root, after build_graph.py:

    python src/rq1.py
"""

import json
import math
from collections import Counter

import numpy as np
import polars as pl
import matplotlib.pyplot as plt

from graph_io import load_graph
from plotstyle import INK_SECONDARY, RELATION_COLOUR, SERIES, apply_style, save

OUT = "data/processed"
K_MIN = 10          # the power-law tail is fitted for k >= K_MIN
summary = {}

apply_style()
g_full, nodes = load_graph(with_merges=True)
g_nomerge, _ = load_graph(with_merges=False)
edges = pl.read_parquet(f"{OUT}/edges.parquet")
n = g_full.vcount()
print(f"G_full: {n:,} nodes, {g_full.ecount():,} edges")
print(f"G_nomerge: {g_nomerge.ecount():,} edges")


# ---------------------------------------------------------------------------
# 1. Children per model (in-degree, because edges are child -> parent)
# ---------------------------------------------------------------------------
def cumulative_distribution(values):
    """Return k and P(K >= k) for every distinct k >= 1 (Topic 4)."""
    values = np.asarray(values)
    values = values[values >= 1]
    k, counts = np.unique(values, return_counts=True)
    at_least_k = np.cumsum(counts[::-1])[::-1]        # number of nodes with degree >= k
    return k, at_least_k / len(values)


def log_binned(values, factor=2.0):
    """Histogram with bins that double in width, normalised by bin width (Topic 4)."""
    values = np.asarray(values)
    values = values[values >= 1]
    n_bins = int(math.ceil(math.log(values.max() + 1, factor)))
    bin_edges = factor ** np.arange(n_bins + 1)       # 1, 2, 4, 8, ...
    counts, _ = np.histogram(values, bins=bin_edges)
    widths = np.diff(bin_edges)
    centres = np.sqrt(bin_edges[:-1] * bin_edges[1:])
    density = counts / widths / len(values)
    keep = counts > 0
    return centres[keep], density[keep]


def tail_exponent(values, k_min=K_MIN):
    """Power-law exponent from the slope of the cumulative distribution.

    If p_k ~ k^(-alpha) in the tail, then P(K >= k) ~ k^(-(alpha - 1)), so a
    straight-line fit on log-log axes has slope -(alpha - 1).
    Only k values reached by at least 10 nodes are used, to avoid the noisy end.
    """
    values = np.asarray(values)
    k, p = cumulative_distribution(values)
    n_pos = (values >= 1).sum()
    use = (k >= k_min) & (p * n_pos >= 10)
    slope, intercept = np.polyfit(np.log10(k[use]), np.log10(p[use]), 1)
    return 1 - slope, slope, intercept, int(k[use].max())


children = np.array(g_full.degree(mode="in"))
alpha, slope, intercept, k_max_fit = tail_exponent(children)
has_children = int((children >= 1).sum())
summary["children"] = {
    "nodes": n,
    "nodes_with_children": has_children,
    "share_with_children": has_children / n,
    "max_children": int(children.max()),
    "mean_children_all_nodes": float(children.mean()),
    "alpha_from_cumulative_slope": float(alpha),
    "fit_range": [K_MIN, k_max_fit],
}
print(f"\n[1] nodes with at least one child: {has_children:,} ({100 * has_children / n:.1f}%)")
print(f"    largest number of children: {children.max():,}")
print(f"    power-law exponent alpha = {alpha:.2f} (cumulative slope, {K_MIN} <= k <= {k_max_fit:,})")

# Optional cross-check with the powerlaw package (maximum likelihood, not in the lectures).
try:
    import powerlaw

    fit = powerlaw.Fit(children[children >= 1], discrete=True, xmin=K_MIN, verbose=False)
    summary["children"]["alpha_powerlaw_package"] = float(fit.power_law.alpha)
    print(f"    cross-check, powerlaw package with xmin={K_MIN}: alpha = {fit.power_law.alpha:.2f}")
except Exception as error:      # the cross-check must never stop the script
    print("    powerlaw cross-check skipped:", error)

k, p = cumulative_distribution(children)
pl.DataFrame({"k": k, "p_at_least_k": p}).write_csv(f"{OUT}/rq1_children_cumulative.csv")

fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.0))
centres, density = log_binned(children)
left.loglog(centres, density, "o-", color=SERIES[0])
left.set(title="Children per model, log-binned", xlabel="children k", ylabel="fraction of models per unit k")
right.loglog(k, p, color=SERIES[0], label="all derivations")
k_line = np.array([K_MIN, k_max_fit])
right.loglog(k_line, 10 ** intercept * k_line ** slope, "--", color=INK_SECONDARY, linewidth=1.2,
             label=f"fit, alpha = {alpha:.2f}")
right.set(title="Cumulative distribution", xlabel="children k", ylabel="P(K >= k)")
right.legend()
save(fig, "rq1_children_distribution")

# The same distribution, split by the relation type of the child.
per_relation = {}
fig, ax = plt.subplots(figsize=(4.2, 3.2))
index = dict(zip(nodes["_id"], nodes["node"]))
for relation, colour in RELATION_COLOUR.items():
    counts = Counter(index[p] for p in edges.filter(pl.col("relation") == relation)["parent_id"])
    values = np.array(list(counts.values()))
    a, s, i, kmax = tail_exponent(values)
    per_relation[relation] = {
        "edges": int(values.sum()), "parents": len(values),
        "max_children": int(values.max()), "alpha": float(a),
    }
    kk, pp = cumulative_distribution(values)
    ax.loglog(kk, pp, color=colour, label=f"{relation} (alpha {a:.2f})")
    print(f"    {relation:<10} edges {values.sum():>8,}  parents {len(values):>7,}  "
          f"max {values.max():>6,}  alpha {a:.2f}")
ax.set(title="Children per model, by relation type", xlabel="children k", ylabel="P(K >= k)")
ax.legend()
save(fig, "rq1_children_by_relation")
summary["children_by_relation"] = per_relation


# ---------------------------------------------------------------------------
# 2. Top-heavy share: how many edges do the best-connected models hold?
# ---------------------------------------------------------------------------
ranked = np.sort(children)[::-1]
cumulative_edges = np.cumsum(ranked) / ranked.sum()
top_share = {}
print("\n[2] share of all edges held by the top models (ranked by children):")
for percent in (0.01, 0.1, 1, 5, 10):
    count = max(1, int(round(n * percent / 100)))
    top_share[f"top_{percent}%"] = {"models": count, "edge_share": float(cumulative_edges[count - 1])}
    print(f"    top {percent:>5}% = {count:>6,} models hold {100 * cumulative_edges[count - 1]:.1f}% of edges")
summary["top_heavy_share"] = top_share

# Only 9.3% of models have any child, so the line above reaches 100% early.
# The same question among models that have at least one child:
parents_ranked = ranked[ranked >= 1]
parent_cumulative = np.cumsum(parents_ranked) / parents_ranked.sum()
top_share_parents = {}
print("    among the models that have at least one child:")
for percent in (1, 5, 10, 20):
    count = max(1, int(round(len(parents_ranked) * percent / 100)))
    top_share_parents[f"top_{percent}%"] = {"models": count, "edge_share": float(parent_cumulative[count - 1])}
    print(f"    top {percent:>5}% = {count:>6,} models hold {100 * parent_cumulative[count - 1]:.1f}% of edges")
summary["top_heavy_share_among_parents"] = top_share_parents

fig, ax = plt.subplots(figsize=(3.6, 3.2))
fraction_of_models = np.arange(1, n + 1) / n
ax.plot(100 * fraction_of_models, 100 * cumulative_edges, color=SERIES[0], label="observed")
# If every model held the same number of edges, the top P% would hold P%.
equal_x = np.logspace(-3, 2, 200)
ax.plot(equal_x, equal_x, "--", color=INK_SECONDARY, linewidth=1.2, label="equal shares")
ax.set(title="Share of edges held by top models", xlabel="top P% of models (by children)",
       ylabel="% of all edges", xscale="log", xlim=(0.001, 100), ylim=(0, 102))
ax.legend(loc="upper left")
save(fig, "rq1_top_heavy_share")


# ---------------------------------------------------------------------------
# 3. Parents per merge
# ---------------------------------------------------------------------------
merges = nodes.filter(pl.col("relation") == "merge")
parent_table = merges.group_by("n_parents").len().sort("n_parents")
parent_table.write_csv(f"{OUT}/rq1_parents_per_merge.csv")
non_merge_multi = nodes.filter((pl.col("relation") != "merge") & (pl.col("n_parents") >= 2)).height
merges2 = merges.filter(pl.col("n_parents") >= 2)
summary["merges"] = {
    "merge_models": merges.height,
    "merges_with_2plus_parents": merges2.height,
    "mean_parents": float(merges2["n_parents"].mean()),
    "max_parents": int(merges2["n_parents"].max()),
    "non_merge_models_with_2plus_parents": non_merge_multi,
}
print(f"\n[3] merge models: {merges.height:,}; with 2+ parents: {merges2.height:,}; "
      f"mean parents {merges2['n_parents'].mean():.2f}; max {merges2['n_parents'].max()}")
print(f"    non-merge models with 2+ parents: {non_merge_multi} (so G_nomerge is a forest)")


# ---------------------------------------------------------------------------
# 4. Weakly connected components, with and without merge edges
# ---------------------------------------------------------------------------
is_root = np.array(nodes["is_root"].to_list())
root_family = nodes["family"].to_list()          # for a root, this is its own family


def component_report(graph, label):
    membership = np.array(graph.connected_components(mode="weak").membership)
    sizes = np.bincount(membership)
    order = np.argsort(sizes)[::-1]
    # Named families among the roots inside each component.
    families_in = {}
    for v in np.flatnonzero(is_root):
        family = root_family[v]
        if family not in ("unknown", "mixed"):
            families_in.setdefault(membership[v], set()).add(family)
    multi_family = sum(1 for s in families_in.values() if len(s) >= 2)
    giant = order[0]
    report = {
        "components": int(len(sizes)),
        "largest": int(sizes[giant]),
        "largest_share_of_nodes": float(sizes[giant] / n),
        "top5_sizes": [int(sizes[c]) for c in order[:5]],
        "components_joining_2plus_named_families": multi_family,
        "named_families_in_largest": sorted(families_in.get(giant, [])),
        "roots_in_largest": int(is_root[membership == giant].sum()),
    }
    print(f"    {label:<10} components {len(sizes):>6,}  largest {sizes[giant]:>7,} "
          f"({100 * sizes[giant] / n:.1f}% of nodes)  "
          f"components joining 2+ named families: {multi_family}")
    return report, sizes


print("\n[4] weakly connected components:")
summary["components_full"], sizes_full = component_report(g_full, "G_full")
summary["components_nomerge"], sizes_nomerge = component_report(g_nomerge, "G_nomerge")
print(f"    named families in the largest component of G_full: "
      f"{len(summary['components_full']['named_families_in_largest'])} "
      f"({', '.join(summary['components_full']['named_families_in_largest'])})")
print(f"    roots in the largest component of G_full: {summary['components_full']['roots_in_largest']:,}")

fig, ax = plt.subplots(figsize=(4.2, 3.2))
for sizes, label, colour in ((sizes_full, "with merges", SERIES[0]), (sizes_nomerge, "without merges", SERIES[1])):
    s, p_s = cumulative_distribution(sizes)
    ax.loglog(s, p_s, color=colour, label=label)
    ax.plot(s[-1], p_s[-1], "o", color=colour, markersize=6)       # the largest component
ax.annotate(f"largest: {sizes_full.max():,}", (sizes_full.max(), 1 / len(sizes_full)),
            textcoords="offset points", xytext=(4, 10), ha="right", color=INK_SECONDARY)
ax.annotate(f"largest: {sizes_nomerge.max():,}", (sizes_nomerge.max(), 1 / len(sizes_nomerge)),
            textcoords="offset points", xytext=(-9, -3), ha="right", color=INK_SECONDARY)
ax.set(title="Component sizes", xlabel="component size s (models)", ylabel="P(S >= s)")
ax.legend(loc="upper right")
save(fig, "rq1_component_sizes")


# ---------------------------------------------------------------------------
# 5. Lineage depth, with and without merge edges
# ---------------------------------------------------------------------------
depth_full = np.array(nodes["depth"].to_list())      # computed in build_graph.py

# Without merge edges every node has at most one parent, so depth is the
# length of the chain up to the root. Follow each chain once and remember it.
single_parent = {}
for c, p in zip(edges.filter(pl.col("relation") != "merge")["child_id"],
                edges.filter(pl.col("relation") != "merge")["parent_id"]):
    single_parent[index[c]] = index[p]
depth_nomerge = np.zeros(n, dtype=int)
done = np.zeros(n, dtype=bool)
for v in range(n):
    chain = []
    x = v
    while not done[x] and x in single_parent:
        chain.append(x)
        x = single_parent[x]
    done[x] = True
    d = depth_nomerge[x]
    for y in reversed(chain):
        d += 1
        depth_nomerge[y] = d
        done[y] = True


def depth_stats(depth):
    non_root = depth[depth >= 1]
    return {
        "max": int(depth.max()),
        "mean_non_root": float(non_root.mean()),
        "share_depth_1": float((non_root == 1).mean()),
        "share_depth_5plus": float((non_root >= 5).mean()),
        "nodes_depth_10plus": int((depth >= 10).sum()),
    }


summary["depth_full"] = depth_stats(depth_full)
summary["depth_nomerge"] = depth_stats(depth_nomerge)
print("\n[5] lineage depth (generations from a root):")
for label, stats in (("G_full", summary["depth_full"]), ("G_nomerge", summary["depth_nomerge"])):
    print(f"    {label:<10} max {stats['max']:>3}  mean {stats['mean_non_root']:.2f}  "
          f"depth 1: {100 * stats['share_depth_1']:.1f}%  depth 5+: {100 * stats['share_depth_5plus']:.1f}%  "
          f"nodes at depth 10+: {stats['nodes_depth_10plus']:,}")
merge_depth = depth_full[np.array(nodes["relation"].to_list()) == "merge"]
summary["depth_of_merges"] = {"mean": float(merge_depth.mean()), "median": float(np.median(merge_depth))}
print(f"    merge models themselves: mean depth {merge_depth.mean():.1f}, median {np.median(merge_depth):.0f}")

fig, ax = plt.subplots(figsize=(4.2, 3.2))
for depth, label, colour in ((depth_full, "with merges", SERIES[0]), (depth_nomerge, "without merges", SERIES[1])):
    d, p_d = cumulative_distribution(depth)
    ax.loglog(d, p_d, "o-", color=colour, label=label, markersize=3)
ax.set(title="Lineage depth", xlabel="depth d (generations from a root)", ylabel="P(D >= d)")
ax.legend(loc="lower left")
save(fig, "rq1_lineage_depth")


# ---------------------------------------------------------------------------
# 6. Do merges join different roots / different families?
# ---------------------------------------------------------------------------
roots_of = nodes["roots"].to_list()
families_of = nodes["families"].to_list()
unknown_root = nodes["has_unknown_root"].to_list()
parents_of = {}
for c, p in zip(edges["child_id"], edges["parent_id"]):
    parents_of.setdefault(index[c], []).append(index[p])

merge_nodes = merges2["node"].to_list()
cross_root = same_family = cross_family = undetermined = 0
pair_counts = Counter()
for v in merge_nodes:
    parents = parents_of[v]
    # Root level: do all parents trace back to exactly the same roots?
    if len({tuple(roots_of[p]) for p in parents}) >= 2:
        cross_root += 1
    # Family level: named families over all parents.
    named = set()
    for p in parents:
        named.update(families_of[p])
    any_unknown = any(unknown_root[p] for p in parents)
    if len(named) >= 2:
        cross_family += 1
        pair_counts[" + ".join(sorted(named))] += 1
    elif len(named) == 1 and not any_unknown:
        same_family += 1
    else:
        undetermined += 1          # an unknown root is involved, so the family is not certain

total = len(merge_nodes)
determined = same_family + cross_family
summary["merge_mixing"] = {
    "merges": total,
    "cross_root": cross_root, "cross_root_share": cross_root / total,
    "cross_family": cross_family, "same_family": same_family, "undetermined": undetermined,
    "cross_family_share_of_all": cross_family / total,
    "cross_family_share_of_determined": cross_family / determined,
    "top_cross_family_combinations": pair_counts.most_common(10),
}
print(f"\n[6] merges with 2+ parents: {total:,}")
print(f"    root level:   parents trace to different roots in {cross_root:,} ({100 * cross_root / total:.1f}%)")
print(f"    family level: same family {same_family:,} ({100 * same_family / total:.1f}%), "
      f"cross-family {cross_family:,} ({100 * cross_family / total:.1f}%), "
      f"undetermined {undetermined:,} ({100 * undetermined / total:.1f}%)")
print(f"    cross-family share among merges with known families: {100 * cross_family / determined:.1f}%")
print("    most common cross-family combinations:")
for combo, count in pair_counts.most_common(8):
    print(f"      {count:>5,}  {combo}")

with open(f"{OUT}/rq1_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"\nsaved {OUT}/rq1_summary.json")
