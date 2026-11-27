# MergeMap

A network analysis of model merging on Hugging Face.
Course project for COMP 6917 Complex Networks, Memorial University, Fall 2026.

A merged model combines the weights of two or more parent models, so merges can join otherwise separate model families. MergeMap builds the lineage graph of 942,088 Hugging Face models and asks four questions:

1. **RQ1** How much do merges connect separate model families?
2. **RQ2** Who merges with whom, and how often do close relatives merge?
3. **RQ3** Which models act as bridges or hubs?
4. **RQ4** How many models would inherit a flaw in a base model, and how much do merges add?

An extension beyond the proposal (lecture Topic 5-5) asks how the network grows: is there preferential attachment, and do merges copy the parent lists of earlier merges?

The final report is `report/MergeMap Report.pdf` (LaTeX source `report/MergeMap_Report.tex`, which reads its figures from `results/`).

After a run, open `results/index.html` (double-click it). It is a results viewer: for each step it shows the key numbers, figures, tables, every saved number and the terminal output, so you don't have to read the terminal or open the folders.

## Quick start

From this folder, in PowerShell:

```
.\mergemap\Scripts\Activate.ps1
python MergeMap.py
```

| Command | What it does | Time |
|---|---|---|
| `python MergeMap.py` | Runs every step, then builds the results page | about 14 to 19 minutes |
| `python MergeMap.py --quick` | Skips the two slow steps (RQ2 and the baselines) if their results already exist | about 1.5 minutes |
| `python MergeMap.py --page` | Only rebuilds `results/index.html` | a few seconds |

If `data/raw/models.parquet` is missing, the first step downloads the pinned snapshot (1.6 GB). If it is present, the step only checks its SHA-256.

`MergeMap.py` shows each step's output and also saves it to `results/<step>/log.txt`. It stops at the first step that fails and names it. The results are reproducible: row orders, ties and random seeds (6917) are fixed, and two full runs give identical files.

**Analysis only.** Steps 4 to 9 need only `data/graph/edges.parquet` and `data/graph/graph_nodes.parquet`. To skip the data steps, run them in order from this folder:

```
python src/4_rq1.py
python src/5_rq2.py
python src/6_rq3.py
python src/7_rq4.py
python src/8_baseline.py
python src/9_build_page.py
```

## Requirements

Python 3.13. The packages and the exact versions used are in `requirements.txt`: `polars`, `pyarrow`, `python-igraph`, `leidenalg`, `numpy`, `matplotlib`, `huggingface_hub` and `powerlaw` (only for a cross-check). The virtual environment `mergemap/` already contains them. To set it up again:

```
python -m venv mergemap
.\mergemap\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Folders

```
MergeMap.py            runs the whole project
README.md              this file
requirements.txt       Python packages (exact versions used)
MergeMap_Plan.md       working plan, decisions and results per phase
src/
  1_download.py        get and check the pinned data snapshot
  2_build_edges.py     node table and cleaned edge list
  3_build_graph.py     lineage graph, depth, roots, family labels
  4_rq1.py             RQ1 structure, plus growth (preferential attachment, age)
  5_rq2.py             RQ2 mixing, inbreeding and copying (slow, ~6 min)
  6_rq3.py             RQ3 hubs and bridges
  7_rq4.py             RQ4 reach and audit coverage
  8_baseline.py        degree-preserving random baselines (slow, ~7 min)
  9_build_page.py      results/index.html
  lib/                 helpers the scripts import (not run directly)
data/
  raw/models.parquet         the pinned snapshot, 3,177,876 models (1.6 GB, not in git)
  graph/nodes.parquet        every model in the snapshot (95 MB, step 2, not in git)
  graph/edges.parquet        cleaned child -> parent edges, 929,941 (step 2)
  graph/graph_nodes.parquet  one row per graph node, 942,088 (step 3)
results/
  index.html           the results viewer (open in a browser)
  log_page.txt         printout of the page build
  run_info.json        when the last run ran, how long each step took
  pipeline/            snapshot check, cleaning counts, graph checks
  rq1/ rq2/ rq3/ rq4/  figures (.png), tables (.csv, .parquet), numbers (*_summary.json), log.txt
  baseline/            random baseline results
presentation/          demo deck MergeMap_Demo.pptx and the scripts that build it
notebooks/             early exploration scripts
report/
  MergeMap Report.pdf  final report (IEEE format, 8 pages)
  MergeMap_Report.tex  LaTeX source
```

Steps can also be run one by one, in order, from this folder, for example `python src/4_rq1.py`.

## Data

- **Source:** [`cfahlgren1/hub-stats`](https://huggingface.co/datasets/cfahlgren1/hub-stats), file `models.parquet`, licence Apache-2.0.
- **Snapshot:** commit `1a8f69d167bd1442c6a31fee5b818e86fc6ae4f7`, uploaded 2026-10-22 13:31 UTC.
- **SHA-256:** `35cb53dfd7847502d3bf7041c080a2468513af44d464f5b7f0028ffea20de738` (1,635,955,091 bytes).
- **Lineage:** the `baseModels` field, which model authors fill in themselves. Each model gives one relation (`finetune`, `adapter`, `quantized` or `merge`) and its parents.

The files in `data/graph/` are derived from this dataset by the scripts in `src/` and are shared under the same licence.

## Graph model

- **Node:** a model that appears in at least one lineage edge.
- **Edge:** child → parent ("derived from"), labelled with the child's relation. So in-degree is the number of children.
- **Cleaning:** self-loops and edges whose parent is newer than the child are removed; parents missing from the snapshot are kept as flagged "ghost" nodes.
- **Family:** each root (a model with no declared parent) is matched against a fixed list of 41 family name patterns (`src/lib/families.py`); a model inherits the families of its roots.

## Methods

From the lectures: topological sort and cycle check, cocitation network, weakly connected components, degree distributions and power laws (log binning, cumulative distribution), PageRank, betweenness, breadth-first search, modularity and Leiden communities, G(n,m) random graphs.

From Topic 5-5 (network formation), added after the proposal: the attachment rate R(k) measured by replaying edges in creation order (preferential attachment, Price's model), age against number of children, and vertex copying of parent lists between merges.

From the proposal, outside the lectures (Newman, *Networks: An Introduction*, 2010): family assortativity and degree-preserving random graphs.

Own implementations: topological sort, lineage depth and root sets, cocitation, PageRank (checked against the Assignment 3 matrix-inverse version and igraph), assortativity (checked against igraph), inbreeding search, reach by BFS, the edge-swap baselines, the attachment-rate replay and the copying search.

## Limitations

- Lineage is self-declared, so all counts are lower bounds.
- 23.5% of merge parents have no recognisable family; family-level results describe the classified part.
- RQ4 assumes a merge inherits fully from every parent.
- One snapshot (22 October 2026); the Hub changes daily.

## Demo deck

`presentation/MergeMap_Demo.pptx` is the 10-minute demo, with speaker notes and timings. It is built from the latest results, so rebuild it after a full run:

```
python presentation/make_visuals.py
cd presentation
npm install
node build_deck.js
```

`make_visuals.py` renders the two 3D pictures and collects every number the slides show into `presentation/assets/deck_data.json`; `build_deck.js` writes the deck with pptxgenjs. The titles use Bahnschrift and the body Segoe UI, both included with Windows.
