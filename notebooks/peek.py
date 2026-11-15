import polars as pl

lf = pl.scan_parquet("data/raw/models.parquet")
print(lf.collect_schema())

cols = ["_id", "id", "author", "createdAt", "downloads", "likes", "baseModels"]
for row in lf.select(cols).head(5).collect().to_dicts():
    print(row)