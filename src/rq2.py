"""RQ2: who merges with whom, and how often do close relatives merge?

Measures
    1. cocitation network of merge parents (own code; Topic 2)
    2. family-to-family merge matrix
    3. family assortativity (Newman [5]) and modularity Q of the family
       partition (Topic 5-3) on the cocitation network
    4. cocitation network compared with a G(n,m) random graph (Topic 5-4)
    5. inbreeding rate at 1, 2, 3 generations and at any depth (own code)
    6. the main numbers again with one merge per (author, parent set)

Output
    data/processed/cocitation_edges.parquet, rq2_*.csv, rq2_summary.json
    figures/rq2_*.png

Run from the project root, after build_graph.py:

    python src/rq2.py
"""

import json
import math
import random
from collections import Counter
from itertools import combinations

import igraph as ig
import numpy as np
import polars as pl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm

from graph_io import load_lineage
from inbreeding import LEVELS, inbreeding_rates
from plotstyle import INK, INK_SECONDARY, SERIES, apply_style, save

OUT = "data/processed"
SEED = 6917
RANDOM_GRAPHS = 100
summary = {}

apply_style()
random.seed(SEED)
nodes, parents_of, merges = load_lineage()
name = nodes["name"].to_list()
family = nodes["family"].to_list()
author = nodes["author"].to_list()
print(f"merges with 2+ parents: {len(merges):,}")


# ---------------------------------------------------------------------------
# 1. Cocitation network of merge parents
# ---------------------------------------------------------------------------
def cocitation(merge_list):
    """Weighted cocitation: weight(a, b) = number of merges that cite both.

    Each merge child points to its parents, so two parents are cocited once
    per merge that lists both. This equals the off-diagonal part of A.A^T
    when A is restricted to merge edges (Topic 2).
    """
    weight = Counter()
    for v in merge_list:
        for a, b in combinations(sorted(parents_of[v]), 2):
            weight[(a, b)] += 1
    return weight


def build_graph(weight):
    """Undirected weighted igraph graph from a cocitation Counter."""
    members = sorted({x for pair in weight for x in pair})
    position = {v: i for i, v in enumerate(members)}
    g = ig.Graph(n=len(members), edges=[(position[a], position[b]) for a, b in weight], directed=False)
    g.es["weight"] = list(weight.values())
    g.vs["node"] = members
    g.vs["family"] = [family[v] for v in members]
    return g


weight = cocitation(merges)
cg = build_graph(weight)
pl.DataFrame({
    "a": [name[a] for a, _ in weight], "b": [name[b] for _, b in weight],
    "weight": list(weight.values()),
}).sort("weight", descending=True).write_parquet(f"{OUT}/cocitation_edges.parquet")

n, m = cg.vcount(), cg.ecount()
total_weight = sum(weight.values())
summary["cocitation"] = {
    "nodes": n, "edges": m, "total_weight": total_weight,
    "mean_degree": 2 * m / n, "max_weight": max(weight.values()),
}
print(f"\n[1] cocitation network: {n:,} parents, {m:,} links, total weight {total_weight:,}, "
      f"mean degree {2 * m / n:.1f}")
strongest = max(weight, key=weight.get)
print(f"    strongest pair ({weight[strongest]} merges): {name[strongest[0]]}  +  {name[strongest[1]]}")


# ---------------------------------------------------------------------------
# 2. Family-to-family merge matrix
# ---------------------------------------------------------------------------
def mixing_counts(weight, weighted=True):
    """Count links between every pair of labels (symmetric)."""
    counts = Counter()
    for (a, b), w in weight.items():
        fa, fb = sorted((family[a], family[b]))
        counts[(fa, fb)] += w if weighted else 1
    return counts


counts = mixing_counts(weight)
label_strength = Counter()
for (fa, fb), w in counts.items():
    label_strength[fa] += w
    label_strength[fb] += w
named = [f for f, _ in label_strength.most_common() if f not in ("unknown", "mixed")]
shown = named[:8] + ["mixed", "unknown"]


def shown_label(f):
    return f if f in shown else "other"


labels = shown[:8] + ["other", "mixed", "unknown"]
matrix = np.zeros((len(labels), len(labels)))
for (fa, fb), w in counts.items():
    i, j = labels.index(shown_label(fa)), labels.index(shown_label(fb))
    matrix[i, j] += w
    if i != j:
        matrix[j, i] += w
pl.DataFrame({"family": labels, **{lab: matrix[:, k].astype(int) for k, lab in enumerate(labels)}}
             ).write_csv(f"{OUT}/rq2_family_matrix.csv")

same = sum(w for (fa, fb), w in counts.items() if fa == fb)
print(f"\n[2] cocited pairs with the same label: {same:,} of {total_weight:,} ({100 * same / total_weight:.1f}%)")

blues = LinearSegmentedColormap.from_list("blues", ["#eaf2fd", "#9ec5f4", "#3987e5", "#184f95", "#0d366b"])
fig, ax = plt.subplots(figsize=(5.4, 4.6))
masked = np.ma.masked_where(matrix == 0, matrix)
image = ax.imshow(masked, cmap=blues, norm=LogNorm(vmin=1, vmax=matrix.max()))
ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
ax.set_yticks(range(len(labels)), labels)
ax.grid(False)
for i in range(len(labels)):
    for j in range(len(labels)):
        value = int(matrix[i, j])
        if value:
            dark = matrix[i, j] > matrix.max() ** 0.5
            ax.text(j, i, f"{value:,}", ha="center", va="center", fontsize=6,
                    color="white" if dark else INK)
ax.set_title("Cocited merge parents, by family")
fig.colorbar(image, ax=ax, shrink=0.8, label="cocited pairs (weighted, log scale)")
save(fig, "rq2_family_matrix")


# ---------------------------------------------------------------------------
# 3. Family assortativity and modularity
# ---------------------------------------------------------------------------
def assortativity_and_modularity(pair_weights, label_of):
    """Assortativity coefficient r and modularity Q from a mixing matrix.

    e[i][j] = fraction of edge ends joining label i to label j, a[i] = row sum.
        Q = sum_i (e_ii - a_i^2)                      (Topic 5-3)
        r = Q / (1 - sum_i a_i^2)                     (Newman [5], eq. 7.80)
    So r is Q divided by the largest value Q could take with these labels.
    """
    e = Counter()
    total = 0
    for (a, b), w in pair_weights.items():
        la, lb = label_of[a], label_of[b]
        e[(la, lb)] += w
        e[(lb, la)] += w
        total += 2 * w
    a_share = Counter()
    for (la, _), w in e.items():
        a_share[la] += w / total
    same_share = sum(w for (la, lb), w in e.items() if la == lb) / total
    expected = sum(s * s for s in a_share.values())
    q = same_share - expected
    return q / (1 - expected), q


def mixing_report(pair_weights, label):
    known = {pair: w for pair, w in pair_weights.items()
             if family[pair[0]] not in ("unknown", "mixed") and family[pair[1]] not in ("unknown", "mixed")}
    unit = {pair: 1 for pair in pair_weights}
    unit_known = {pair: 1 for pair in known}
    report = {}
    for key, data in (("all_labels_weighted", pair_weights), ("all_labels_unweighted", unit),
                      ("named_only_weighted", known), ("named_only_unweighted", unit_known)):
        r, q = assortativity_and_modularity(data, family)
        report[key] = {"assortativity": r, "modularity_Q": q, "links": len(data)}
    print(f"    {label}")
    for key, value in report.items():
        print(f"      {key:<24} r = {value['assortativity']:.3f}   Q = {value['modularity_Q']:.3f}   "
              f"links {value['links']:,}")
    return report


print("\n[3] family assortativity r and modularity Q on the cocitation network:")
summary["mixing"] = mixing_report(weight, "all merges")

# Cross-check the own formula against igraph on the unweighted graph.
label_ids = {f: i for i, f in enumerate(sorted(set(cg.vs["family"])))}
types = [label_ids[f] for f in cg.vs["family"]]
r_igraph = cg.assortativity_nominal(types, directed=False)
q_igraph = cg.modularity(types)
summary["mixing"]["igraph_check_unweighted"] = {"assortativity": r_igraph, "modularity_Q": q_igraph}
print(f"    igraph cross-check (unweighted, all labels): r = {r_igraph:.3f}   Q = {q_igraph:.3f}")


# ---------------------------------------------------------------------------
# 4. Cocitation network versus a G(n,m) random graph
# ---------------------------------------------------------------------------
def structure(g):
    """Clustering coefficient, giant-component fraction, mean path length in the giant."""
    giant = g.connected_components().giant()
    return {
        "clustering": g.transitivity_undirected(),
        "giant_fraction": giant.vcount() / g.vcount(),
        "mean_path_length": giant.average_path_length(),
    }


def giant_fraction_theory(c):
    """Solve S = 1 - exp(-c S) by repeated substitution (Topic 5-4)."""
    s = 1.0
    for _ in range(1000):
        s = 1 - math.exp(-c * s)
    return s


c = 2 * m / n
observed = structure(cg)
samples = [structure(ig.Graph.Erdos_Renyi(n=n, m=m)) for _ in range(RANDOM_GRAPHS)]
random_mean = {k: float(np.mean([s[k] for s in samples])) for k in observed}
random_sd = {k: float(np.std([s[k] for s in samples])) for k in observed}
theory = {
    "clustering": c / (n - 1),
    "giant_fraction": giant_fraction_theory(c),
    "mean_path_length": math.log(n) / math.log(c),
}
summary["versus_random_graph"] = {
    "n": n, "m": m, "mean_degree_c": c, "observed": observed,
    "gnm_theory": theory, "gnm_sample_mean": random_mean, "gnm_sample_sd": random_sd,
    "samples": RANDOM_GRAPHS,
}
print(f"\n[4] cocitation network vs G(n,m), n = {n:,}, m = {m:,}, mean degree c = {c:.2f}")
print(f"    {'':<20}{'observed':>10}{'G(n,m) theory':>16}{'G(n,m) sampled':>22}")
for key in observed:
    print(f"    {key:<20}{observed[key]:>10.4f}{theory[key]:>16.4f}"
          f"{random_mean[key]:>14.4f} +- {random_sd[key]:.4f}")
pl.DataFrame({
    "measure": list(observed), "observed": list(observed.values()),
    "gnm_theory": [theory[k] for k in observed],
    "gnm_sample_mean": [random_mean[k] for k in observed],
    "gnm_sample_sd": [random_sd[k] for k in observed],
}).write_csv(f"{OUT}/rq2_versus_random_graph.csv")


# ---------------------------------------------------------------------------
# 5. Inbreeding
# ---------------------------------------------------------------------------
def inbreeding_report(merge_list, label):
    rates = inbreeding_rates([parents_of[v] for v in merge_list], parents_of)
    print(f"    {label} ({len(merge_list):,} merges)")
    print(f"      {'related within':<16}{'ancestor type':>14}{'common ancestor':>17}{'total':>8}")
    for level in LEVELS:
        r = rates[level]
        print(f"      {str(level):<16}{100 * r['ancestor']:>13.1f}%{100 * r['common_ancestor']:>16.1f}%"
              f"{100 * r['total']:>7.1f}%")
    return {str(level): rates[level] for level in LEVELS}


print("\n[5] inbreeding: share of merges with at least one related pair of parents")
summary["inbreeding"] = inbreeding_report(merges, "all merges")

fig, ax = plt.subplots(figsize=(4.4, 3.2))
x = np.arange(len(LEVELS))
ancestor = np.array([100 * summary["inbreeding"][str(level)]["ancestor"] for level in LEVELS])
common = np.array([100 * summary["inbreeding"][str(level)]["common_ancestor"] for level in LEVELS])
ax.bar(x, ancestor, width=0.6, color=SERIES[0], edgecolor="white", linewidth=1.5,
       label="one parent is an ancestor of another")
ax.bar(x, common, width=0.6, bottom=ancestor, color=SERIES[1], edgecolor="white", linewidth=1.5,
       label="parents share an ancestor")
for xi, total in zip(x, ancestor + common):
    ax.text(xi, total + 1.5, f"{total:.1f}%", ha="center", color=INK_SECONDARY)
ax.set_xticks(x, ["1", "2", "3", "any depth"])
ax.set(title="Merges with related parents", xlabel="related within (generations)",
       ylabel="% of merges", ylim=(0, 100))
ax.grid(axis="x", visible=False)
ax.legend(loc="upper left")
save(fig, "rq2_inbreeding")


# ---------------------------------------------------------------------------
# 6. The same numbers with one merge per (author, parent set)
# ---------------------------------------------------------------------------
seen = set()
unique_merges = []
for v in merges:
    key = (author[v], frozenset(parents_of[v]))
    if key not in seen:
        seen.add(key)
        unique_merges.append(v)
by_author = Counter(author[v] for v in merges)
top_authors = by_author.most_common(5)
print(f"\n[6] one merge per (author, parent set): {len(unique_merges):,} of {len(merges):,} merges kept")
print(f"    merge authors: {len(by_author):,}; the 10 most active made "
      f"{100 * sum(c for _, c in by_author.most_common(10)) / len(merges):.1f}% of merges")
print(f"    most active: {', '.join(f'{a} ({c})' for a, c in top_authors)}")
summary["deduplicated"] = {
    "merges_kept": len(unique_merges),
    "authors": len(by_author),
    "top10_author_share": sum(c for _, c in by_author.most_common(10)) / len(merges),
    "mixing": mixing_report(cocitation(unique_merges), "deduplicated merges"),
    "inbreeding": inbreeding_report(unique_merges, "deduplicated merges"),
}

with open(f"{OUT}/rq2_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"\nsaved {OUT}/rq2_summary.json")
