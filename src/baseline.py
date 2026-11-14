"""Phase 7: are the mixing and inbreeding patterns real, or would random
merging produce them too?

Two degree-preserving random baselines, as promised in the proposal
(Newman [5]; the configuration-model idea is not in the lecture slides):

A. Shuffled merges (main baseline).
   The merge table lists, for every merge, its parents. The parents are
   swapped between merges at random, many times, so that
       * every merge keeps its number of parents,
       * every parent keeps its number of merges,
       * no merge gets the same parent twice or itself as a parent,
       * every parent is older than the merge it is given (or is a ghost).
   Each swap takes two merge edges (c1, p1) and (c2, p2) and turns them into
   (c1, p2) and (c2, p1) when the rules above still hold. The rest of the
   lineage graph (fine-tunes, adapters, quantizations) is left as it is.
   On each shuffled graph the inbreeding search and the cocitation mixing
   are measured again.

B. Rewired cocitation network.
   The cocitation network itself is rewired with igraph's rewire(): every
   parent keeps its number of cocitation links, the links go to random
   other parents. Family assortativity and clustering are measured again.
   This baseline breaks the clique structure that merges create, so it is
   the weaker one; it is kept because the proposal names it.

For every measure: observed value, baseline mean and standard deviation,
z = (observed - mean) / sd, and the share of baseline runs that reach the
observed value.

Output
    data/processed/baseline_summary.json, baseline_*.csv
    figures/baseline_*.png

Run from the project root, after build_graph.py:

    python src/baseline.py
"""

import json
import os
import random

import igraph as ig
import numpy as np
import polars as pl
import matplotlib.pyplot as plt

import mixing
from graph_io import load_lineage
from inbreeding import LEVELS, inbreeding_rates
from plotstyle import INK_SECONDARY, MUTED, SERIES, apply_style, save

OUT = "data/processed"
SEED = 6917
RUNS = int(os.environ.get("BASELINE_RUNS", 100))      # set lower only for a quick test
SWAPS_PER_EDGE = 10
summary = {"runs": RUNS, "seed": SEED, "swaps_per_edge": SWAPS_PER_EDGE}

apply_style()
random.seed(SEED)                       # igraph's rewire() also uses Python's random module
nodes, parents_of, merges = load_lineage()
family = nodes["family"].to_list()
created = nodes["createdAt"].to_list()
ghost = nodes["ghost"].to_list()
print(f"merges with 2+ parents: {len(merges):,}")


def compare(observed, samples):
    samples = np.asarray(samples, dtype=float)
    mean, sd = float(samples.mean()), float(samples.std(ddof=1))
    return {
        "observed": float(observed), "baseline_mean": mean, "baseline_sd": sd,
        "z": (observed - mean) / sd if sd > 0 else float("inf"),
        "share_of_runs_at_or_above_observed": float((samples >= observed).mean()),
        "baseline_min": float(samples.min()), "baseline_max": float(samples.max()),
    }


# ---------------------------------------------------------------------------
# Observed values (the same numbers as rq2.py)
# ---------------------------------------------------------------------------
observed_inbreeding = inbreeding_rates([parents_of[v] for v in merges], parents_of)
observed_weight = mixing.cocitation(merges, parents_of)
observed_mixing = mixing.mixing_variants(observed_weight, family)


# ---------------------------------------------------------------------------
# A. Shuffled merges
# ---------------------------------------------------------------------------
def older(p, c):
    """True if parent p may be given to merge c: p is a ghost (no date, no
    parents of its own) or p was created strictly before c."""
    if ghost[p] or created[p] is None or created[c] is None:
        return True
    return created[p] < created[c]


merge_edges = [(c, p) for c in merges for p in parents_of[c]]
assert all(older(p, c) for c, p in merge_edges), "an observed merge edge breaks the age rule"
print(f"merge edges to shuffle: {len(merge_edges):,}")


def shuffled_parents(rng, same_family=False):
    """One shuffled copy of the merge table, by repeated edge swaps.

    same_family=True only swaps two parents that carry the same family label
    ("unknown" and "mixed" count as labels). Then every merge keeps the
    families of its parents, which respects the practical limit that only
    models of one architecture can be merged. This is the stricter baseline.
    """
    child = [c for c, _ in merge_edges]
    parent = [p for _, p in merge_edges]
    has = {c: set(parents_of[c]) for c in merges}
    m = len(child)
    accepted = 0
    for _ in range(SWAPS_PER_EDGE * m):
        i, j = rng.randrange(m), rng.randrange(m)
        c1, p1, c2, p2 = child[i], parent[i], child[j], parent[j]
        if c1 == c2 or p1 == p2:
            continue
        if same_family and family[p1] != family[p2]:
            continue
        if p2 in has[c1] or p1 in has[c2] or p2 == c1 or p1 == c2:
            continue
        if not (older(p2, c1) and older(p1, c2)):
            continue
        has[c1].remove(p1)
        has[c1].add(p2)
        has[c2].remove(p2)
        has[c2].add(p1)
        parent[i], parent[j] = p2, p1
        accepted += 1
    new_parents = dict(parents_of)          # non-merge models keep their parent
    for c in merges:
        new_parents[c] = []
    for c, p in zip(child, parent):
        new_parents[c].append(p)
    return new_parents, accepted / (SWAPS_PER_EDGE * m)


rng = random.Random(SEED)
shuffled_inbreeding = {str(level): {"total": [], "ancestor": [], "common_ancestor": []} for level in LEVELS}
shuffled_mixing = {key: [] for key in observed_mixing}
acceptance = []
changed_share = []
print(f"\nA. shuffled merges, {RUNS} runs")
for run in range(RUNS):
    shuffled, accepted_share = shuffled_parents(rng)
    acceptance.append(accepted_share)
    changed_share.append(np.mean([p not in parents_of[c] for c in merges for p in shuffled[c]]))
    rates = inbreeding_rates([shuffled[v] for v in merges], shuffled)
    for level in LEVELS:
        for kind in ("total", "ancestor", "common_ancestor"):
            shuffled_inbreeding[str(level)][kind].append(rates[level][kind])
    variants = mixing.mixing_variants(mixing.cocitation(merges, shuffled), family)
    for key in shuffled_mixing:
        shuffled_mixing[key].append(variants[key]["assortativity"])
    if (run + 1) % 10 == 0:
        print(f"    run {run + 1:>3}: inbred within 1 = {100 * rates[1]['total']:.1f}%, "
              f"r (all labels, weighted) = {variants['all_labels_weighted']['assortativity']:.3f}")

summary["shuffle_acceptance_rate"] = float(np.mean(acceptance))
summary["shuffle_share_of_merge_edges_changed"] = float(np.mean(changed_share))
print(f"    swaps accepted: {100 * np.mean(acceptance):.1f}%; "
      f"merge edges that differ from the real data: {100 * np.mean(changed_share):.1f}%")

summary["inbreeding"] = {
    str(level): {kind: compare(observed_inbreeding[level][kind], shuffled_inbreeding[str(level)][kind])
                 for kind in ("total", "ancestor", "common_ancestor")}
    for level in LEVELS
}

# A2. The stricter version: parents are only swapped within the same family.
# Every merge keeps the families of its parents, so the cocitation family mix
# is unchanged by construction; only inbreeding is measured.
family_inbreeding = {str(level): {"total": [], "ancestor": [], "common_ancestor": []} for level in LEVELS}
family_acceptance, family_changed = [], []
print(f"\nA2. merges shuffled within families, {RUNS} runs")
for run in range(RUNS):
    shuffled, accepted_share = shuffled_parents(rng, same_family=True)
    family_acceptance.append(accepted_share)
    family_changed.append(np.mean([p not in parents_of[c] for c in merges for p in shuffled[c]]))
    rates = inbreeding_rates([shuffled[v] for v in merges], shuffled)
    for level in LEVELS:
        for kind in ("total", "ancestor", "common_ancestor"):
            family_inbreeding[str(level)][kind].append(rates[level][kind])
    if (run + 1) % 10 == 0:
        print(f"    run {run + 1:>3}: inbred within 1 = {100 * rates[1]['total']:.1f}%")
summary["within_family_acceptance_rate"] = float(np.mean(family_acceptance))
summary["within_family_share_of_merge_edges_changed"] = float(np.mean(family_changed))
print(f"    swaps accepted: {100 * np.mean(family_acceptance):.1f}%; "
      f"merge edges that differ from the real data: {100 * np.mean(family_changed):.1f}%")
summary["inbreeding_within_family"] = {
    str(level): {kind: compare(observed_inbreeding[level][kind], family_inbreeding[str(level)][kind])
                 for kind in ("total", "ancestor", "common_ancestor")}
    for level in LEVELS
}
summary["mixing_shuffled_merges"] = {
    key: compare(observed_mixing[key]["assortativity"], shuffled_mixing[key]) for key in observed_mixing
}


# ---------------------------------------------------------------------------
# B. Rewired cocitation network
# ---------------------------------------------------------------------------
members = sorted({x for pair in observed_weight for x in pair})
position = {v: i for i, v in enumerate(members)}
cg = ig.Graph(n=len(members), edges=[(position[a], position[b]) for a, b in observed_weight], directed=False)
member_family = [family[v] for v in members]


def graph_mixing(g):
    """Unweighted assortativity (all labels, named only) and clustering of g."""
    pairs = {(members[e.source], members[e.target]): 1 for e in g.es}
    variants = mixing.mixing_variants(pairs, family)
    return (variants["all_labels_unweighted"]["assortativity"],
            variants["named_only_unweighted"]["assortativity"],
            g.transitivity_undirected())


obs_all, obs_named, obs_clustering = graph_mixing(cg)
rewired = {"all": [], "named": [], "clustering": []}
print(f"\nB. rewired cocitation network ({cg.vcount():,} parents, {cg.ecount():,} links), {RUNS} runs")
for run in range(RUNS):
    g = cg.copy()
    g.rewire(n=SWAPS_PER_EDGE * g.ecount(), allowed_edge_types="simple")
    a, b, c = graph_mixing(g)
    rewired["all"].append(a)
    rewired["named"].append(b)
    rewired["clustering"].append(c)
summary["rewired_cocitation"] = {
    "assortativity_all_labels_unweighted": compare(obs_all, rewired["all"]),
    "assortativity_named_only_unweighted": compare(obs_named, rewired["named"]),
    "clustering": compare(obs_clustering, rewired["clustering"]),
}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
def line(label, result, percent=False):
    f = (lambda x: f"{100 * x:6.1f}%") if percent else (lambda x: f"{x:7.3f}")
    sd = f"{100 * result['baseline_sd']:.2f} pts" if percent else f"{result['baseline_sd']:.3f}"
    print(f"    {label:<34}{f(result['observed'])}  {f(result['baseline_mean'])} +- {sd:<9}"
          f"z = {result['z']:8.1f}   runs >= observed: {100 * result['share_of_runs_at_or_above_observed']:.0f}%")


print(f"\n{'':4}{'measure':<34}{'observed':>8}  {'baseline mean +- sd':>20}")
print("  A. shuffled merges: inbreeding (share of merges with a related pair of parents)")
for level in LEVELS:
    line(f"related within {level}", summary["inbreeding"][str(level)]["total"], percent=True)
    line(f"  of which ancestor type", summary["inbreeding"][str(level)]["ancestor"], percent=True)
print("  A2. merges shuffled within families: inbreeding")
for level in LEVELS:
    line(f"related within {level}", summary["inbreeding_within_family"][str(level)]["total"], percent=True)
    line(f"  of which ancestor type", summary["inbreeding_within_family"][str(level)]["ancestor"], percent=True)
print("  A. shuffled merges: family assortativity of the cocitation network")
for key in observed_mixing:
    line(key, summary["mixing_shuffled_merges"][key])
print("  B. rewired cocitation network")
for key, result in summary["rewired_cocitation"].items():
    line(key, result)

rows = []
for level in LEVELS:
    for kind in ("total", "ancestor", "common_ancestor"):
        rows.append({"baseline": "shuffled merges", "measure": f"inbreeding within {level} ({kind})",
                     **summary["inbreeding"][str(level)][kind]})
        rows.append({"baseline": "shuffled within families", "measure": f"inbreeding within {level} ({kind})",
                     **summary["inbreeding_within_family"][str(level)][kind]})
for key, result in summary["mixing_shuffled_merges"].items():
    rows.append({"baseline": "shuffled merges", "measure": f"assortativity {key}", **result})
for key, result in summary["rewired_cocitation"].items():
    rows.append({"baseline": "rewired cocitation", "measure": key, **result})
pl.DataFrame(rows).write_csv(f"{OUT}/baseline_results.csv")

with open(f"{OUT}/baseline_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"\nsaved {OUT}/baseline_summary.json")


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(5.0, 3.4))
x = np.arange(len(LEVELS))
bars = [
    ("observed", SERIES[0], [summary["inbreeding"][str(level)]["total"]["observed"] for level in LEVELS], None),
    ("shuffled within families", SERIES[1],
     [summary["inbreeding_within_family"][str(level)]["total"]["baseline_mean"] for level in LEVELS],
     [summary["inbreeding_within_family"][str(level)]["total"]["baseline_sd"] for level in LEVELS]),
    ("shuffled merges", MUTED,
     [summary["inbreeding"][str(level)]["total"]["baseline_mean"] for level in LEVELS],
     [summary["inbreeding"][str(level)]["total"]["baseline_sd"] for level in LEVELS]),
]
width = 0.26
for k, (label, colour, values, sds) in enumerate(bars):
    offset = (k - 1) * width
    values = [100 * v for v in values]
    ax.bar(x + offset, values, width=width - 0.02, color=colour, label=label,
           yerr=None if sds is None else [100 * s for s in sds], capsize=2)
    for xi, value in zip(x, values):
        ax.text(xi + offset, value + 1.5, f"{value:.0f}", ha="center", fontsize=6.5, color=INK_SECONDARY)
ax.set_xticks(x, ["1", "2", "3", "any depth"])
ax.set(title="Merges with related parents: real vs random", xlabel="related within (generations)",
       ylabel="% of merges", ylim=(0, 100))
ax.grid(axis="x", visible=False)
ax.legend(loc="upper left")
save(fig, "baseline_inbreeding")

fig, ax = plt.subplots(figsize=(4.6, 3.0))
labels = ["all labels", "named only"]
obs_r = [summary["mixing_shuffled_merges"]["all_labels_unweighted"]["observed"],
         summary["mixing_shuffled_merges"]["named_only_unweighted"]["observed"]]
shuf_r = [summary["mixing_shuffled_merges"]["all_labels_unweighted"]["baseline_mean"],
          summary["mixing_shuffled_merges"]["named_only_unweighted"]["baseline_mean"]]
rew_r = [summary["rewired_cocitation"]["assortativity_all_labels_unweighted"]["baseline_mean"],
         summary["rewired_cocitation"]["assortativity_named_only_unweighted"]["baseline_mean"]]
y = np.arange(len(labels))
ax.barh(y + 0.25, obs_r, height=0.24, color=SERIES[0], label="observed")
ax.barh(y, shuf_r, height=0.24, color=MUTED, label="shuffled merges")
ax.barh(y - 0.25, rew_r, height=0.24, color=SERIES[2], label="rewired cocitation")   # orange = within families
for yi, values in zip(y, zip(obs_r, shuf_r, rew_r)):
    for offset, value in zip((0.25, 0, -0.25), values):
        ax.text(max(value, 0) + 0.01, yi + offset, f"{value:.2f}", va="center", fontsize=7,
                color=INK_SECONDARY)
ax.set_yticks(y, labels)
ax.set(title="Family assortativity of merge parents", xlabel="assortativity r (unweighted)", xlim=(-0.1, 1.1))
ax.axvline(0, color=MUTED, linewidth=0.8)
ax.grid(axis="y", visible=False)
ax.legend(loc="lower right", fontsize=7)
save(fig, "baseline_assortativity")
