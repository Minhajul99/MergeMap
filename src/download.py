"""Download the pinned snapshot of the Hugging Face model metadata.

Source:   cfahlgren1/hub-stats (Apache-2.0), file models.parquet
Snapshot: commit 1a8f69d167bd1442c6a31fee5b818e86fc6ae4f7, uploaded 2026-10-22 13:31 UTC

The dataset is overwritten every day, so the commit is pinned and the file is
checked against its SHA-256. Run from the project root:

    python src/download.py
"""

import hashlib
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO_ID = "cfahlgren1/hub-stats"
FILENAME = "models.parquet"
REVISION = "1a8f69d167bd1442c6a31fee5b818e86fc6ae4f7"
SHA256 = "35cb53dfd7847502d3bf7041c080a2468513af44d464f5b7f0028ffea20de738"
RAW_DIR = Path("data/raw")


def sha256_of(path: Path) -> str:
    """Hash the file in 8 MB blocks so it never has to fit in memory."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    target = RAW_DIR / FILENAME

    if target.exists():
        print(f"{target} already exists, checking it ...")
    else:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {FILENAME} at commit {REVISION[:8]} (about 1.6 GB) ...")
        hf_hub_download(
            repo_id=REPO_ID,
            filename=FILENAME,
            repo_type="dataset",
            revision=REVISION,
            local_dir=RAW_DIR,
        )

    actual = sha256_of(target)
    if actual != SHA256:
        raise SystemExit(
            f"SHA-256 mismatch for {target}\n  expected {SHA256}\n  got      {actual}\n"
            "This is not the pinned snapshot. Delete the file and run again."
        )
    print(f"OK: {target} matches the pinned snapshot ({target.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
