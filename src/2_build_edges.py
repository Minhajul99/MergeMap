"""Step 2: build the node table and the cleaned edge list from the raw snapshot.

Output
    data/graph/nodes.parquet           every model in the snapshot (not in git, 95 MB)
    data/graph/edges.parquet           cleaned child -> parent edges
    results/pipeline/edges_summary.json   the counts printed below

Run from the project root, after 1_download.py:

    python src/2_build_edges.py
"""

import json

import polars as pl

from lib.paths import EDGES, NODES, RAW, results_dir

OUT = results_dir("pipeline")
summary = {}

# Row order must be the same on every run: node numbers, tie-breaking and the
# Leiden communities all depend on it. So every unique() keeps the file order
# (for the 13 duplicated models, the first row in the file wins), and both
# tables are sorted before they are saved.

raw_rows = pl.scan_parquet(RAW).select(pl.len()).collect().item()
nodes = (
    pl.scan_parquet(RAW)
    .select("_id", "id", "author", "createdAt", "downloads", "likes")
    .unique(subset="_id", keep="first", maintain_order=True)
    .sort("_id")
    .collect()
)

print("nodes:", nodes.height)
nodes.write_parquet(NODES)
summary["raw_rows"] = raw_rows
summary["models"] = nodes.height
summary["duplicate_rows_removed"] = raw_rows - nodes.height

edges_raw = (
    pl.scan_parquet(RAW)
    .select("_id", "createdAt", "baseModels")
    .unique(subset="_id", keep="first", maintain_order=True)
    .rename({"_id": "child_id", "createdAt": "child_created"})
    .filter(pl.col("baseModels").is_not_null())
    .unnest("baseModels")
    .explode("models")
    # Position of the parent in the model's own list (0 = listed first).
    .with_columns(pl.int_range(pl.len()).over("child_id").alias("parent_pos"))
    .unnest("models")
    .rename({"_id": "parent_id", "id": "parent_name"})
    .collect()
)

print("raw edges:", edges_raw.height)
print(edges_raw.group_by("relation").len().sort("len", descending=True))
summary["models_declaring_a_base"] = edges_raw["child_id"].n_unique()
summary["raw_edges"] = edges_raw.height

# ---------------------------------------------------------------------------
# Cleaning. Each rule logs how many edges it removes or flags.
# ---------------------------------------------------------------------------

# (a) Self-loops: a model that lists itself as its own base model.
edges = edges_raw.filter(pl.col("child_id") != pl.col("parent_id"))
print("self-loops removed:", edges_raw.height - edges.height)
summary["self_loops_removed"] = edges_raw.height - edges.height

# (b) Ghost parents: the parent is not in the dump (deleted, private or gated).
#     They are kept and flagged, not dropped.
parent_info = nodes.select(
    pl.col("_id").alias("parent_id"),
    pl.col("createdAt").alias("parent_created"),
    pl.lit(True).alias("in_dump"),
)
edges = edges.join(parent_info, on="parent_id", how="left").with_columns(
    pl.col("in_dump").is_null().alias("ghost")
).drop("in_dump")
print(
    "edges to ghost parents:", edges["ghost"].sum(),
    "| distinct ghost parents:", edges.filter("ghost")["parent_id"].n_unique(),
)
summary["edges_to_ghost_parents"] = int(edges["ghost"].sum())
summary["ghost_parents"] = edges.filter("ghost")["parent_id"].n_unique()

# (c) Parent strictly newer than the child. Equal dates are kept, and ghost
#     parents have no date, so they are kept too.
before = edges.height
edges = edges.filter(
    pl.col("parent_created").is_null()
    | pl.col("child_created").is_null()
    | (pl.col("parent_created") <= pl.col("child_created"))
)
print("parent-newer-than-child removed:", before - edges.height)
summary["newer_parent_edges_removed"] = before - edges.height

# (d) Duplicate (child, parent) pairs.
before = edges.height
edges = edges.sort("child_id", "parent_pos").unique(
    subset=["child_id", "parent_id"], keep="first", maintain_order=True
)
print("duplicate edges removed:", before - edges.height)
summary["duplicate_edges_removed"] = before - edges.height

# ---------------------------------------------------------------------------
# Save. Edge direction in the graph is child -> parent ("derived from").
# Rows are sorted by child, then by the parent's position in the child's list.
# ---------------------------------------------------------------------------
edges = edges.sort("child_id", "parent_pos").select(
    "child_id", "parent_id", "relation", "ghost", "parent_name"
)
edges.write_parquet(EDGES)

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
n_nodes = pl.concat([edges["child_id"], edges["parent_id"]]).n_unique()
parents_per_child = edges.group_by("child_id", "relation").len()
merges_2plus = parents_per_child.filter(
    (pl.col("relation") == "merge") & (pl.col("len") >= 2)
).height
multi_parent_non_merge = parents_per_child.filter(
    (pl.col("relation") != "merge") & (pl.col("len") >= 2)
).height
by_relation = edges.group_by("relation").len().sort("len", descending=True)

print()
print("clean edges:", edges.height)
print("distinct children:", edges["child_id"].n_unique())
print("distinct nodes in graph:", n_nodes)
print("merges with 2+ parents:", merges_2plus)
print("non-merge models with 2+ parents:", multi_parent_non_merge)
print(by_relation)

summary.update({
    "clean_edges": edges.height,
    "children": edges["child_id"].n_unique(),
    "graph_nodes": n_nodes,
    "merges_with_2plus_parents": merges_2plus,
    "non_merge_models_with_2plus_parents": multi_parent_non_merge,
    "edges_by_relation": dict(zip(by_relation["relation"], by_relation["len"])),
})
with open(f"{OUT}/edges_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)
print(f"saved {OUT}/edges_summary.json")
