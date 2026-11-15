import pyarrow.parquet as pq
import pandas as pd
from collections import Counter

PATH = r"data\raw\models.parquet"  # run from the project root

pf = pq.ParquetFile(PATH)
print("Total rows (models):", pf.metadata.num_rows)
print("\nColumns:")
print(pf.schema.names)

# Find the base-model column
base_col = next((c for c in pf.schema.names if "basemodel" in c.lower()), None)
print("\nBase-model column:", base_col)

if base_col:
    df = pd.read_parquet(PATH, columns=["id", base_col])
    print("\nThree example values:")
    for v in df[base_col].dropna().head(3):
        print(repr(v)[:300])

    with_parent = df[base_col].apply(
        lambda v: v is not None and len(v) > 0 if hasattr(v, "__len__") else False
    ).sum()
    print("\nModels with at least one parent:", with_parent)

    # Count relation types, if stored as dicts with a 'relation' key
    rel = Counter()
    merge_models = 0
    for v in df[base_col].dropna():
        try:
            items = list(v) if not isinstance(v, dict) else [v]
            rels = [str(x.get("relation", "")).lower() for x in items if isinstance(x, dict)]
            rel.update(rels)
            if "merge" in rels:
                merge_models += 1
        except Exception:
            pass
    print("Relation counts:", dict(rel))
    print("Merged models:", merge_models)