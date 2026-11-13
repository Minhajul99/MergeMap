import polars as pl

RAW = "data/raw/models.parquet"

nodes = (
    pl.scan_parquet(RAW)
    .select("_id", "id", "author", "createdAt", "downloads", "likes")
    .unique(subset="_id", keep="first")
    .collect()
)

print("nodes:", nodes.height)
nodes.write_parquet("data/processed/nodes.parquet")

edges_raw = (
    pl.scan_parquet(RAW)
    .select("_id", "createdAt", "baseModels")
    .unique(subset="_id", keep="first")
    .rename({"_id": "child_id", "createdAt": "child_created"})
    .filter(pl.col("baseModels").is_not_null())
    .unnest("baseModels")
    .explode("models")
    .unnest("models")
    .rename({"_id": "parent_id", "id": "parent_name"})
    .collect()
)

print("raw edges:", edges_raw.height)
print(edges_raw.group_by("relation").len().sort("len", descending=True))

# ---------------------------------------------------------------------------
# Cleaning. Each rule logs how many edges it removes or flags.
# ---------------------------------------------------------------------------

# (a) Self-loops: a model that lists itself as its own base model.
edges = edges_raw.filter(pl.col("child_id") != pl.col("parent_id"))
print("self-loops removed:", edges_raw.height - edges.height)

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

# (c) Parent strictly newer than the child. Equal dates are kept, and ghost
#     parents have no date, so they are kept too.
before = edges.height
edges = edges.filter(
    pl.col("parent_created").is_null()
    | pl.col("child_created").is_null()
    | (pl.col("parent_created") <= pl.col("child_created"))
)
print("parent-newer-than-child removed:", before - edges.height)

# (d) Duplicate (child, parent) pairs.
before = edges.height
edges = edges.unique(subset=["child_id", "parent_id"], keep="first", maintain_order=True)
print("duplicate edges removed:", before - edges.height)

# ---------------------------------------------------------------------------
# Save. Edge direction in the graph is child -> parent ("derived from").
# ---------------------------------------------------------------------------
edges = edges.select("child_id", "parent_id", "relation", "ghost", "parent_name")
edges.write_parquet("data/processed/edges.parquet")

# ---------------------------------------------------------------------------
# Summary, to compare against the expected counts in MergeMap_Plan.md.
# ---------------------------------------------------------------------------
n_nodes = pl.concat([edges["child_id"], edges["parent_id"]]).n_unique()
parents_per_child = edges.group_by("child_id", "relation").len()
merges_2plus = parents_per_child.filter(
    (pl.col("relation") == "merge") & (pl.col("len") >= 2)
).height
multi_parent_non_merge = parents_per_child.filter(
    (pl.col("relation") != "merge") & (pl.col("len") >= 2)
).height

print()
print("clean edges:", edges.height)
print("distinct children:", edges["child_id"].n_unique())
print("distinct nodes in graph:", n_nodes)
print("merges with 2+ parents:", merges_2plus)
print("non-merge models with 2+ parents:", multi_parent_non_merge)
print(edges.group_by("relation").len().sort("len", descending=True))