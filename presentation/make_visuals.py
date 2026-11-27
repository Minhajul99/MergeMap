"""Render the 3D visuals for the demo deck and collect its numbers.

Reads only files that the pipeline wrote (results/ and data/graph/), so the
deck always matches the latest run. Writes into presentation/assets/:
    hero_network.png    3D cocitation network of the most-cited merge parents
    skyline.png         3D bars: descendants of the top base models, with and without merges
    deck_data.json      every number the slides show

Run from the project root, after MergeMap.py:

    python presentation/make_visuals.py
"""

import json
import math
import random
import sys
from pathlib import Path

import igraph as ig
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
RESULTS = ROOT / "results"
ASSETS = Path(__file__).resolve().parent / "assets"
ASSETS.mkdir(exist_ok=True)

BG = "#1B1C20"
WHITE = "#FFFFFF"
MUTED = "#A9ADB6"
AMBER = "#F5A524"
STEEL = "#6FA8DC"
FAMILY_COLOUR = {
    "mistral": AMBER, "llama": STEEL, "qwen": "#4FC3A1", "gemma": "#E57373",
    "phi": "#B39DDB", "other": "#8D939C", "unknown": "#5C616A", "mixed": "#8D939C",
}
SEED = 6917


def load(path):
    return json.loads((RESULTS / path).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Numbers for the slides
# ---------------------------------------------------------------------------
edges_s = load("pipeline/edges_summary.json")
graph_s = load("pipeline/graph_summary.json")
snapshot = load("pipeline/snapshot.json")
rq1, rq2, rq3, rq4 = (load(f"rq{i}/rq{i}_summary.json") for i in (1, 2, 3, 4))
base = load("baseline/baseline_summary.json")
run_info = load("run_info.json")

top_kids = pl.read_csv(RESULTS / "rq3" / "rq3_top_children.csv").head(5)
top_bt = pl.read_csv(RESULTS / "rq3" / "rq3_top_betweenness.csv").head(3)
top_roots = pl.read_csv(RESULTS / "rq4" / "rq4_top_roots.csv")
recipes = pl.read_csv(RESULTS / "rq2" / "rq2_repeated_recipes.csv")
cov = rq4["audit_coverage"]
rate = pl.read_csv(RESULTS / "rq1" / "rq1_attachment_rate.csv")

data = {
    "snapshot": {"date": snapshot["uploaded"][:10], "commit": snapshot["revision"][:10]},
    "models": edges_s["models"],
    "declaring_base": edges_s["models_declaring_a_base"],
    "graph_nodes": graph_s["nodes"],
    "graph_edges": graph_s["edges"],
    "roots": graph_s["roots"],
    "edges_by_relation": edges_s["edges_by_relation"],
    "merges": edges_s["merges_with_2plus_parents"],
    "merge_models": rq1["merges"]["merge_models"],
    "merge_share_of_linked": rq1["merges"]["merge_models"] / edges_s["models_declaring_a_base"],
    "largest_without": rq1["components_nomerge"]["largest"],
    "largest_with": rq1["components_full"]["largest"],
    "components_without": rq1["components_nomerge"]["components"],
    "components_with": rq1["components_full"]["components"],
    "depth_without": rq1["depth_nomerge"]["max"],
    "depth_with": rq1["depth_full"]["max"],
    "families_in_giant": len(rq1["components_full"]["named_families_in_largest"]),
    "alpha": rq1["children"]["alpha_from_cumulative_slope"],
    "top_0_01_share": rq1["top_heavy_share"]["top_0.01%"]["edge_share"],
    "top_0_01_models": rq1["top_heavy_share"]["top_0.01%"]["models"],
    "assort_named": rq2["mixing"]["named_only_unweighted"]["assortativity"],
    "assort_all": rq2["mixing"]["all_labels_weighted"]["assortativity"],
    "same_label_share": None,
    "inbred": {k: rq2["inbreeding"][k]["total"] for k in ("1", "2", "3", "any")},
    "inbred_within_family": {k: base["inbreeding_within_family"][k]["total"]["baseline_mean"] for k in ("1", "2", "3", "any")},
    "inbred_shuffled": {k: base["inbreeding"][k]["total"]["baseline_mean"] for k in ("1", "2", "3", "any")},
    "copying": rq2["copying"],
    "copying_within_family": base["copying_within_family"]["share_copying"]["baseline_mean"],
    "copying_shuffled": base["copying_shuffled_merges"]["share_copying"]["baseline_mean"],
    "repeat_within_family": base["copying_within_family"]["share_exact_repeat"]["baseline_mean"],
    "top_recipe": {"merges": int(recipes["merges"][0]), "authors": int(recipes["authors"][0])},
    "crowd_recipe": None,
    "hubs": [{"model": m, "children": int(c)} for m, c in zip(top_kids["model"], top_kids["children"])],
    "bridges": [m for m in top_bt["model"]],
    "merge_share_nodes": rq3["lineage_betweenness"]["merge_share_of_all_nodes"],
    "merge_share_betweenness": rq3["lineage_betweenness"]["share_of_total_betweenness_held_by_merges"],
    "merge_share_top100_bridges": rq3["lineage_betweenness"]["merge_share_of_top"]["100"],
    "beta": rq1["growth"]["kernel_exponent_beta"],
    "age_rho": rq1["growth"]["spearman_age_children_models_with_children"],
    "rate_k": [float(x) for x in rate["k_bin_centre"]],
    "rate_r": [float(x) for x in rate["attachment_rate"]],
    "reach_without": rq4["root_reach"]["total_without_merges"],
    "reach_with": rq4["root_reach"]["total_with_merges"],
    "reach_added": rq4["root_reach"]["added_share"],
    "multi_root": rq4["multi_root_exposure"]["models_with_2plus_roots"],
    "max_roots": rq4["multi_root_exposure"]["max_roots_of_one_model"],
    "coverage_k": [1, 10, 100, 1000],
    "coverage_pagerank": [cov["by PageRank"][k] for k in ("1", "10", "100", "1000")],
    "coverage_random": [cov["random models with a child"][k] for k in ("1", "10", "100", "1000")],
    "coverage_nomerge": [cov["by reach, without merges"][k] for k in ("1", "10", "100", "1000")],
    "merge_parents_unknown": graph_s["merge_parents_unknown"] / graph_s["distinct_merge_parents"],
    "pagerank_check": rq3["pagerank_checks"]["matrix_inverse_largest_difference"],
    "run_seconds": sum((s.get("seconds") or 0) for s in run_info["steps"]),
    "families": graph_s["named_families_in_list"],
    "run_steps": [{"script": st["script"], "description": st.get("description", ""), "seconds": st.get("seconds")}
                  for st in run_info["steps"]],
}
crowd = recipes.sort("authors", descending=True).row(0, named=True)
data["crowd_recipe"] = {"merges": crowd["merges"], "authors": crowd["authors"], "parents": crowd["parents"]}
# Share of cocited parent pairs (weighted by merges) whose two parents carry the same label,
# the same number 5_rq2.py prints in its section 2.
co_edges = pl.read_parquet(RESULTS / "rq2" / "cocitation_edges.parquet")
node_family = pl.read_parquet(ROOT / "data" / "graph" / "graph_nodes.parquet").select("name", "family")
fam_of = dict(zip(node_family["name"], node_family["family"]))
same = sum(w for a, b, w in co_edges.iter_rows() if fam_of.get(a) == fam_of.get(b))
data["same_label_share"] = same / co_edges["weight"].sum()
(ASSETS / "deck_data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
print("saved deck_data.json")


# ---------------------------------------------------------------------------
# Visual 1: 3D cocitation network (title slide and RQ2)
# ---------------------------------------------------------------------------
def hero_network(n_nodes=260):
    co = pl.read_parquet(RESULTS / "rq2" / "cocitation_edges.parquet")
    nodes = pl.read_parquet(ROOT / "data" / "graph" / "graph_nodes.parquet").select("name", "family")
    fam = dict(zip(nodes["name"], nodes["family"]))
    strength = {}
    for a, b, w in co.iter_rows():
        strength[a] = strength.get(a, 0) + w
        strength[b] = strength.get(b, 0) + w
    top = sorted(strength, key=lambda m: (-strength[m], m))[:n_nodes]
    pos = {m: i for i, m in enumerate(top)}
    links = [(pos[a], pos[b], w) for a, b, w in co.iter_rows() if a in pos and b in pos]
    g = ig.Graph(n=len(top), edges=[(a, b) for a, b, _ in links])
    random.seed(SEED)
    # Families form separate clusters. One force layout squeezes each cluster
    # into a dot, so every connected component gets its own 3D layout, scaled
    # by the cube root of its size, and the components are spread on a spiral.
    comps = sorted(g.connected_components(), key=lambda c: (-len(c), min(c)))
    xyz = np.zeros((len(top), 3))
    golden = math.pi * (3 - math.sqrt(5))
    for i, comp in enumerate(comps):
        radius = 0.16 * len(comp) ** (1 / 3)
        if len(comp) == 1:
            local = np.zeros((1, 3))
        else:
            sub = g.subgraph(comp)
            local = np.array(sub.layout_kamada_kawai_3d(maxiter=60 * sub.vcount()).coords)
            local -= local.mean(axis=0)
            local /= max(np.abs(local).max(), 1e-9)
        r = 0 if i == 0 else 0.55 + 0.9 * math.sqrt(i / len(comps))
        centre = np.array([r * math.cos(i * golden), r * math.sin(i * golden), 0.35 * math.sin(1.7 * i)])
        for j, v in enumerate(comp):
            xyz[v] = centre + radius * local[j]
    xyz -= xyz.mean(axis=0)
    xyz /= np.abs(xyz).max()

    fig = plt.figure(figsize=(16, 9), dpi=300)
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0, 0, 1, 1], projection="3d")
    ax.set_facecolor((0, 0, 0, 0))
    ax.set_axis_off()
    w_max = max(w for _, _, w in links)
    for a, b, w in links:
        t = math.log1p(w) / math.log1p(w_max)
        ax.plot(*zip(xyz[a], xyz[b]), color=WHITE, alpha=0.05 + 0.22 * t, linewidth=0.3 + 1.2 * t)
    colours = [FAMILY_COLOUR.get(fam.get(m, "unknown"), FAMILY_COLOUR["other"]) for m in top]
    s = np.array([strength[m] for m in top], dtype=float)
    size = 18 + 520 * np.sqrt(s / s.max())
    ax.scatter(*xyz.T, s=size * 5.5, c=colours, alpha=0.07, depthshade=False, linewidths=0)   # glow
    ax.scatter(*xyz.T, s=size * 2.2, c=colours, alpha=0.18, depthshade=False, linewidths=0)
    ax.scatter(*xyz.T, s=size, c=colours, alpha=0.95, depthshade=True, edgecolors=BG, linewidths=0.6)
    ax.view_init(elev=24, azim=38)
    ax.set_box_aspect((1.9, 1.9, 0.9), zoom=1.35)
    ax.set_xlim(-1, 1); ax.set_ylim(-1, 1); ax.set_zlim(-1, 1)
    fig.savefig(ASSETS / "hero_network.png", transparent=True)
    plt.close(fig)
    present = sorted({fam.get(m, "unknown") if fam.get(m) in FAMILY_COLOUR else "other" for m in top})
    print(f"saved hero_network.png ({len(top)} models, {len(links)} links), families: {present}")
    return present


# ---------------------------------------------------------------------------
# Visual 2: 3D skyline of the top base models (RQ4)
# ---------------------------------------------------------------------------
def skyline(n_roots=8):
    rows = top_roots.head(n_roots)
    names = [r.split("/")[-1] for r in rows["root"]]
    without = rows["reach_without_merges"].to_numpy()
    added = rows["added_by_merges"].to_numpy()
    fig = plt.figure(figsize=(12, 7), dpi=250)
    fig.patch.set_alpha(0)
    ax = fig.add_axes([-0.06, -0.08, 1.12, 1.16], projection="3d")
    ax.set_facecolor((0, 0, 0, 0))
    x = np.arange(n_roots) * 1.5
    y = np.zeros(n_roots)
    width = depth = 0.85
    ax.bar3d(x, y, np.zeros(n_roots), width, depth, without, color="#5B7290", shade=True,
             edgecolor="#2A2F3A", linewidth=0.4)
    visible = added / without > 0.01          # only draw the merge share where it can be seen
    ax.bar3d(x[visible], y[visible], without[visible], width, depth, added[visible], color=AMBER, shade=True,
             edgecolor="#9C6A10", linewidth=0.4)
    for xi, name in zip(x, names):
        ax.text(xi + width / 2, -0.25, 0, name, color=MUTED, fontsize=10, ha="right", va="top")
    ax.set_axis_off()
    ax.view_init(elev=22, azim=-62)
    ax.set_box_aspect((3.2, 1.0, 1.25))
    ax.set_zlim(0, max(without + added) * 1.02)
    fig.savefig(ASSETS / "skyline.png", transparent=True)
    plt.close(fig)
    print("saved skyline.png")


def crop_to_content(name, pad=0.03):
    """Cut the empty transparent margin away and return the final size."""
    from PIL import Image
    path = ASSETS / name
    im = Image.open(path)
    left, top, right, bottom = im.getbbox()
    dx, dy = int((right - left) * pad), int((bottom - top) * pad)
    im = im.crop((max(left - dx, 0), max(top - dy, 0), min(right + dx, im.width), min(bottom + dy, im.height)))
    im.save(path)
    return {"w": im.width, "h": im.height}


def inbred_example(max_ancestors=10):
    """A popular merge whose parents are a model and that model's own descendant,
    small enough to draw. Returns the nodes (with a generation level and an order
    within the level) and edges of its family tree."""
    from collections import deque
    from lib.graph_io import load_lineage

    nodes_t, parents_of, merges = load_lineage()
    names = nodes_t["name"].to_list()
    rel = nodes_t["relation"].to_list()
    kids = np.array(nodes_t["n_children"].to_list())

    def ancestors(v, limit):
        seen, queue = {v}, deque([v])
        while queue:
            x = queue.popleft()
            for p in parents_of.get(x, ()):
                if p not in seen:
                    seen.add(p)
                    queue.append(p)
                    if len(seen) > limit + 1:
                        return None
        seen.discard(v)
        return seen

    best = None
    for v in merges:
        ps = parents_of[v]
        if len(ps) != 2:
            continue
        anc = ancestors(v, max_ancestors)
        if anc is None or len(anc) < 5:
            continue
        a, b = ps
        anc_b, anc_a = ancestors(b, 50) or set(), ancestors(a, 50) or set()
        if a in anc_b:
            pair = (a, b)                    # a is an ancestor of b
        elif b in anc_a:
            pair = (b, a)
        else:
            continue
        key = (kids[v], -len(anc), names[v])
        if best is None or key > best[0]:
            best = (key, v, anc, pair)
    _, v, anc, (a, b) = best
    members = anc | {v}
    level = {}

    def lev(x):
        if x not in level:
            ps = [p for p in parents_of.get(x, ()) if p in members]
            level[x] = 0 if not ps else 1 + max(lev(p) for p in ps)
        return level[x]

    for x in members:
        lev(x)
    rows = {}
    for x in members:
        rows.setdefault(level[x], []).append(x)
    order = {}
    for lv in sorted(rows):
        rows[lv].sort(key=lambda x: (np.mean([order[p] for p in parents_of.get(x, ()) if p in order] or [0]), names[x]))
        for i, x in enumerate(rows[lv]):
            order[x] = i - (len(rows[lv]) - 1) / 2
    # The inbred link: the path from b up to a, plus the merge's own edge to a.
    prev, queue = {b: None}, deque([b])
    while queue:
        x = queue.popleft()
        for p in parents_of.get(x, ()):
            if p in members and p not in prev:
                prev[p] = x
                queue.append(p)
    hot = {(v, a)}
    x = a
    while prev.get(x) is not None:
        hot.add((prev[x], x))
        x = prev[x]
    tree_nodes = [{"id": int(x), "name": names[x], "label": names[x].split("/")[-1],
                   "relation": rel[x] or "base model", "children": int(kids[x]),
                   "level": level[x], "order": float(order[x]),
                   "role": "merge" if x == v else "inbred" if x == a else "parent" if x == b else ""}
                  for x in sorted(members, key=lambda x: (level[x], order[x]))]
    tree_edges = [{"child": int(x), "parent": int(p), "hot": (x, p) in hot}
                  for x in members for p in parents_of.get(x, ()) if p in members]
    print(f"inbred example: {names[v]} ({len(members)} models); parent {names[a]} is an ancestor of {names[b]}")
    return {"merge": names[v], "a": names[a], "b": names[b], "nodes": tree_nodes, "edges": tree_edges,
            "levels": max(level.values()) + 1, "width": max(len(r) for r in rows.values())}


data["inbred_tree"] = inbred_example()
families_present = hero_network()
skyline()
data["network_families"] = families_present
data["image_size"] = {"hero_network": crop_to_content("hero_network.png"), "skyline": crop_to_content("skyline.png")}
(ASSETS / "deck_data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
print("image sizes:", data["image_size"])
