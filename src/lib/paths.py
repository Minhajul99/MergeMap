"""Every file location in one place. All paths are relative to the project root,
so every script must be run from there (MergeMap.py does this for you)."""

from pathlib import Path

RAW = "data/raw/models.parquet"

GRAPH_DIR = Path("data/graph")
NODES = str(GRAPH_DIR / "nodes.parquet")              # every model in the snapshot
EDGES = str(GRAPH_DIR / "edges.parquet")              # cleaned child -> parent edges
GRAPH_NODES = str(GRAPH_DIR / "graph_nodes.parquet")  # one row per graph node

RESULTS = Path("results")


def results_dir(step):
    """Folder for one step's figures, tables and summary, created if missing."""
    folder = RESULTS / step
    folder.mkdir(parents=True, exist_ok=True)
    return folder.as_posix()
