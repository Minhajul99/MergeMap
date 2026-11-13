# MergeMap: Project Plan

COMP 6917 Complex Networks. Created Nov 12, 2026. Revised Nov 12, 2026 against the lecture slides, the project regulation and the local data.

**Rule for this plan:** metrics and algorithms come from the lectures (Topics 0–5), with two exceptions kept from the submitted proposal by decision on Nov 12, 2026: **family assortativity** and **degree-preserving random graphs**. Both are in the reference book (Newman [5]); cite it when they are used. Nothing else from outside the lectures is added.

**Deadlines (from `Project_Regulation.pdf`):**
- Nov 27 or Dec 7, in class: 10-minute demo plus 2-minute Q/A.
- Dec 7, 11:59 pm: report (8 pages maximum, LaTeX PDF preferred) and a zip with code, data, processed metric data and a readme.

**"Steps 1–4" means the first four steps of the course workflow:** 1 data set, 2 graph model, 3 metrics, 4 algorithms implemented. Steps 5–6 (knowledge, understanding) are for the report. So by Nov 27 every algorithm must run, but the interpretation can still be rough.

**Marks:** the report is 20 of 40, graded on "quality and novelty of the knowledge discovered". Findings matter more than the number of metrics.

---

## Part A: Lecture coverage

### In the lectures: keep

| Plan item | Lecture |
|---|---|
| Directed acyclic graph, cycle check, topological order | Topic 2; Assignment 2 (`topo_sort.py`) |
| Cocitation and bibliographic coupling (A·Aᵀ, Aᵀ·A) | Topic 2, Topic 3 |
| Bipartite networks and projections | Topic 2 |
| Weakly connected components, giant component | Topics 2, 4, 5-4 |
| Degree distribution, hubs, power law, log binning, cumulative distribution, top-heavy share | Topic 4 |
| Path lengths, small-world effect, diameter | Topic 4, Topic 5-4 |
| Degree centrality, PageRank, hubs and authorities (HITS) | Topic 3; Assignment 3 (`PageRank.py`) |
| BFS, shortest paths, betweenness | Topic 5 |
| Community detection by modularity maximization; Louvain and Leiden are named | Topic 5-3 |
| Modularity Q with group labels | Topic 5-3 |
| Random graphs G(n,m) and G(n,p): expected clustering coefficient, giant component, path length | Topic 5-4 |
| Random failure versus hub failure | Topic 4 (one bullet) |

### Not in the lectures: kept, replaced or marked

| Was in the plan | Problem | Now |
|---|---|---|
| Family assortativity (`assortativity_nominal`) | Assortativity is not in any slide deck | **Kept, as the proposal promises it.** Cite Newman [5]. Also report modularity Q with family labels as the groups (Topic 5-3): it is the same quantity before normalization, so it ties the result to the lectures at no extra cost. |
| NMI / ARI for communities versus families | Not in the lectures | Compare Q of the family partition with Q of the detected communities, plus a community-by-family table. |
| `powerlaw.Fit` with lognormal comparison | Maximum-likelihood fitting is not in the lectures | Log-binned histogram and cumulative distribution on log-log axes; exponent from the slope of the cumulative plot (Topic 4). `powerlaw` only as an optional cross-check. |
| Degree-preserving random graphs | The configuration model is not in the lectures | **Kept as the main baseline, as the proposal promises it.** Cite Newman [5]. G(n,m) (Topic 5-4) is used only for the structural comparison of the cocitation network. |

### Lecture content the plan was not using: added

- **Top-heavy share (Lorenz curve):** share of all derivation edges held by the top P% of models (Topic 4). Direct evidence for hubs.
- **Cocitation network versus G(n,m):** clustering coefficient against c/(n−1), giant-component fraction against S = 1 − e^(−cS), mean path length against ln n / ln c (Topic 5-4). This restores the "path lengths" promised in the proposal, on the network where they mean something.
- **Why PageRank and not eigenvector centrality:** in an acyclic directed graph eigenvector centrality is zero for every node (Topic 3). One sentence in the report.
- **HITS (optional, cheap):** on child → parent edges, authorities are base models and hubs are merges built from many good bases. Only add if time allows.

### Left out on purpose

Max-flow/min-cut, Kernighan–Lin partitioning, Katz centrality, closeness. They are in the lectures but answer none of the four research questions.

---

## Part B: Changes to the submitted proposal

State these on the first slide of the demo and in the report.

1. **Edge direction: child → parent ("derived from").** The proposal says parent → child. The lectures define cocitation of i and j as the number of vertices with outgoing edges pointing to both, so merge parents are cocited only if the merge child points to them. In-degree then counts children, and PageRank collects at base models. With the proposal's direction, RQ3's in-degree would count parents and the "cocitation" network would be bibliographic coupling.
2. **Mixing measure:** unchanged from the proposal (family assortativity). Modularity Q by family is reported next to it.
3. **Baseline:** unchanged from the proposal (degree-preserving random graphs), now specified: rewiring of the cocitation graph for assortativity, and a shuffle of the merge-child-to-parent table for inbreeding. Both keep degrees fixed.
4. **Family labels:** a fixed list of named families matched on root names; other roots are `unknown`. Report cross-family rates with and without `unknown`. Without this, any model that declares no parent becomes its own family and cross-family merging is overstated.
5. **Missing parents:** keep as flagged ghost nodes, do not drop. Dropping them splits families.
6. **RQ4 wording:** the data has no flaw labels. RQ4 measures how many models descend from each base model and how much merges add. State the assumption that a merge inherits fully from every parent.
7. **Power-law fit:** only on the number of children. The number of parents has no tail (see Part C).
8. **Path lengths:** lineage depth on the DAG; shortest paths on the cocitation network.
9. **Timestamp rule:** drop an edge when the parent is strictly newer than the child. Equal dates are kept, so the 2022-03-02 placeholder causes no false drops between old models. This removes 3,430 edges (0.37%); only 35 involve the placeholder date.
10. **Novelty wording:** "to our knowledge". Horwitz et al. [3] already analyse merges. The references were not checked in this review.

---

## Part C: Data facts (local `models.parquet`, downloaded Oct 22, 2026)

Measured Nov 12, 2026.

- 3,177,876 models. 902,524 (28%) declare a base model.
- `baseModels` column: `{relation, models: [{_id, id}]}`. One relation per child. Join on `_id`.
- Relation counts: finetune 361,479; adapter 332,515; quantized 193,211; merge 15,319.
- **Every finetune, adapter and quantized model has exactly one parent.** Only merges have more. So without merge edges the graph is a forest of trees, and merge edges are the only thing that turns it into a DAG. This is a clean structural fact for RQ1.
- Merges with 2 or more parents: **15,119**. With one parent: 200. Parent counts: 2 → 8,798; 3 → 2,568; 4 → 1,624; 5 → 795; then a tail past 12.
- Merges are 1.7% of models that declare a parent. The effect of merges on components may be small. Report what the data shows.
- 15,119 merges is enough for the family matrix, modularity and inbreeding rates. Per-family results for small families will be noisy.
- 935,448 declared edges in total. Self-loops: 2,072.
- **Missing parents:** 14,006 edges (1.5%) point to 3,431 parents that are not in the dump; 13,822 children are affected. Only 77 of these match an existing model by name, so matching by name does not recover them.
- **697 merges (4.6%) have at least one missing parent.** Dropping missing parents would turn some of them into one-parent merges and remove them from RQ2. Ghost nodes keep them.
- Parent strictly newer than child: 3,430 edges (0.37%).
- `createdAt`: 29,561 models carry the placeholder 2022-03-02. Latest date is 2026-10-22.
- File size 1.64 GB. Read only the needed columns.

**Snapshot (confirmed Nov 12, 2026):** the local file is exactly `cfahlgren1/hub-stats` commit `1a8f69d167bd1442c6a31fee5b818e86fc6ae4f7`, uploaded 2026-10-22 13:31 UTC. SHA-256 `35cb53dfd7847502d3bf7041c080a2468513af44d464f5b7f0028ffea20de738`, 1,635,955,091 bytes. `src/download.py` pins that commit and checks the hash. The licence is Apache-2.0, confirmed on the dataset page. Put the commit, hash and licence in the readme.

### Probe results (Nov 12, 2026)

A quick pure-Python pass over the cleaned edges. These are preview numbers, not final results; the real pipeline must reproduce them.

- Graph: 942,088 nodes, 929,941 edges, 44,867 roots, 3,431 ghost nodes. No cycles after cleaning.
- **RQ1:** largest weakly connected component is 43,660 nodes without merge edges and **418,549 with them** (44% of all nodes). Components fall from 60,177 to 41,637.
- **RQ2:** in 85.5% of merges the parents trace back to different roots. This is the root level, not the family level: `Qwen2.5-7B` and `Qwen2.5-1.5B` are different roots of one family. In **24.3%** of merges one parent is an ancestor of another (inbreeding depth 0). 40.2% of merges have a merge as a parent.
- **RQ4:** total root reach rises from 862,654 to 1,135,867 with merge edges (+32%). `Mistral-7B-v0.1` +26.6%, `Meta-Llama-3-8B` +34.9%, `FLUX.1-dev` +0.0%. Merging is concentrated in a few LLM families.
- **Roots:** top 100 roots cover 58% of non-root nodes, top 1,000 cover 82%. 22,107 roots have a single descendant. The largest roots are clearly named: FLUX, Qwen, Gemma, Llama, Mistral, DistilBERT, SDXL, SmolLM, BERT, Whisper, GPT-2.
- 20.2% of merges have only parents that declare no base model.
- The whole pass ran in about a minute, so scale is not a problem for anything except betweenness.

### Decisions on the open risks (Nov 12, 2026)

- **Family labels at two levels.** Root level needs no rule and is fully objective; report it first. Family level uses a regex list applied to the names of **all** roots, built from the top 200 roots by reach. Report the share of merge parents left `unknown`.
- **If behind schedule, cut in this order:** HITS, betweenness on the lineage graph, the per-author repeat of RQ2.
- **Snapshot:** resolved; see the snapshot note above.
- **References:** open the three arXiv pages and confirm titles and authors before the report.

---

## Part D: Exact edits for the proposal

Each row is one sentence to replace. Sections not listed stay as they are.

| Section | Current text | Replace with |
|---|---|---|
| IV. Graph Model | "Node = model; directed edge parent → child, labeled by relation type." | "Node = model; directed edge child → parent (*derived from*), labeled by the child's relation type." |
| IV. Graph Model | "Each model gets a family label from its root base model(s)." | "Roots are models with no declared parent. Roots matching a fixed list of named families (Llama, Mistral, Qwen, ...) get that label; other roots are *unknown*. Each model inherits the labels of its roots." |
| V. Structure (RQ1) | "degree distributions with power-law fits, weakly connected components, and path lengths" | "in-degree (children) distribution with power-law fit, weakly connected components, lineage depth, and path lengths in the cocitation network" |
| V. Centrality (RQ3) | "in-degree, PageRank, approximate betweenness" | No change needed. With child → parent edges, in-degree counts children and is correct. |
| V. Risk reach (RQ4) | "number of descendants of each base model, with and without merges, and the effect of removing top models" | "number of descendants of each base model, with and without merges, and the share of total reach covered by the top-*k* models" |
| V. Baseline | "degree-preserving random graphs, to test if mixing and inbreeding patterns are real" | "degree-preserving random graphs (rewired cocitation network for mixing; shuffled merge-to-parent assignments for inbreeding), to test if the patterns are real" |
| II. RQ4 | "How many models inherit a flawed base model, and how much do merges add?" | "How many models would inherit a flaw in a base model, and how much do merges add?" |
| II. Related work | "None study the merge network itself" | "To our knowledge, none study the merge network itself" |
| VII. Challenges | "we drop self-loops, missing models, and parents newer than children" | "we drop self-loops and edges whose parent is newer than the child; parents missing from the dump are kept as flagged nodes" |
| VIII. Timeline | "Nov 11: proposal, graph built." | "Nov 11: proposal. Nov 15: graph built." |

---

## Phase 0: Setup (Nov 12) — mostly done

- [x] Git repository, venv `mergemap/` with `polars`, `pyarrow`, `python-igraph`, `leidenalg`, `powerlaw`, `numpy`, `matplotlib`, `huggingface_hub`.
- [x] `models.parquet` downloaded; it lives at `data/raw/models.parquet`.
- [x] Add `data/raw/` and `mergemap/` to `.gitignore`.
- [x] Create folders: `src/`, `data/processed/`, `figures/`, `notebooks/`, `report/`.

## Phase 1: Data (Nov 12–13) — workflow step 1

Done Nov 12 by `src/build_edges.py`. Output: `data/processed/nodes.parquet` (3,177,863 models) and `data/processed/edges.parquet` (929,941 edges, 942,088 nodes, 15,046 merges with 2 or more parents). Logged: 2,072 self-loops removed, 14,006 edges to 3,431 ghost parents kept, 3,430 newer-parent edges removed, 0 duplicates. The raw file has 13 duplicate model rows, removed first.

- [x] `src/download.py`: `hf_hub_download(repo_id="cfahlgren1/hub-stats", filename="models.parquet", repo_type="dataset", revision=<commit sha>)`, saving to `data/raw/`.
- [x] Read only `_id`, `id`, `author`, `createdAt`, `downloads`, `likes`, `baseModels`.
- [x] Edge list `(child_id, parent_id, relation)` keyed on `_id`. Node table with `_id`, `id`, `author`, `createdAt`, `downloads`, `likes`.
- [x] Go/no-go gate: 15,119 merges with 2 or more parents. Go.
- [x] Merge definition, frozen: `baseModels.relation == "merge"`.

## Phase 2: Graph model (Nov 13–15) — workflow step 2

Done Nov 12.

- `src/build_graph.py` writes `data/processed/graph_nodes.parquet`, one row per node: depth, roots, family, parent and child counts.
- `src/families.py` holds the frozen family pattern list (41 families, matched on the repo name after `owner/`).
- `src/graph_io.py` has `load_graph(with_merges=True/False)`. It rebuilds `G_full` or `G_nomerge` in igraph from the two parquet files in about a second, so no pickled graphs are saved.
- One-parent merges are not a separate flag: they are the rows with `relation == "merge"` and `n_parents == 1`.

Results:

- 942,088 nodes, 929,941 edges, no cycles (own topological sort and igraph `is_dag()` agree).
- 44,867 roots. Deepest lineage: 151 generations. 632,360 nodes are at depth 1.
- `G_full`: 41,637 weak components, largest 418,549. `G_nomerge`: 881,911 edges, 60,177 components, largest 43,660.
- **Family coverage:** 47.8% of roots get a named family, but they are the large ones: 85.7% of non-root models get a named family or `mixed`, and 14.3% are `unknown`.
- **Weak spot: 23.3% of distinct merge parents are `unknown`** (2,360 of 10,125). The largest unknown roots are models with names like `Marcoro14-7B-slerp` that declare no base model and cannot be identified by name. Report family-level results with and without `unknown`, and root-level results first.
- 1,005 non-root models are `mixed`. 12,293 models have a named family but also at least one unknown root (`has_unknown_root`).

- [x] Drop self-loops and duplicate edges. Log counts.
- [x] Keep missing parents as ghost nodes. Log count.
- [x] Drop edges where the parent is strictly newer than the child (ghost parents have no date and are kept). Log count; expect about 3,430.
- [x] Nodes are models that appear in at least one edge.
- [x] Directed graph, edges child → parent.
- [x] **Own implementation:** cycle check and topological order, reusing the Assignment 2 topological sort. Break and log any cycles.
- [x] Flag the 200 merges with one known parent: reach only.
- [x] Family labels: roots are nodes with out-degree 0. Fixed regex list of named families; the rest `unknown`. A node takes the families of all its roots; more than one named family is `mixed`. Freeze the list.
- [x] Save `G_full` and `G_nomerge`, and the edge list as parquet (the file to submit).
- [x] Sanity check against Laufer et al. [1] (done Nov 12; the paper gives no relation-type shares, so four other stated facts were compared):
  - Finetune edges: the paper counts 191,072 in its 1.86-million-model snapshot. Our graph, cut at the date our dump reaches 1.86 million models (2025-08-22), has 191,155. Difference 0.04%. The cut date is approximate, because deleted models are missing from our dump.
  - Model with the most children: `black-forest-labs/FLUX.1-dev` in both.
  - Depth: the paper reports "nearly 40 generations" using the first-listed parent for merges. Ours is 39 under the same rule. With all merge parents it is 151.
  - Without merges no model has more than one parent, and `createdAt` is back-filled to 2022-03-02: both hold in our data.
  - The reference itself is confirmed: title, authors and arXiv number match.

## Phase 3: RQ1, structure (Nov 16–17)

Done Nov 12 by `src/rq1.py` (figures in `figures/rq1_*.png`, numbers in `data/processed/rq1_summary.json`). `src/plotstyle.py` sets the look of every figure.

Results:

- **Children per model:** only 87,535 models (9.3%) have any child. The largest has 43,421. Power-law exponent from the cumulative slope: alpha = 1.92 for 10 ≤ k ≤ 7,291 (the `powerlaw` package gives 1.86). By relation: finetune 1.88, adapter 1.89, quantized 2.20, merge 2.60. The merge curve bends, so its exponent is a rough summary, not a clean power law.
- **Top-heavy share:** the top 94 models (0.01%) hold 42.1% of all edges; the top 942 hold 69.0%. Among models with at least one child, the top 1% hold 68.3%.
- **Merges:** 15,046 with 2 or more parents, 3.17 parents on average, 97 at most.
- **Components:** 60,177 without merge edges, largest 43,660 (4.6% of nodes). 41,637 with merge edges, largest 418,549 (44.4%). The largest component contains 2,448 roots and 28 named families.
- **Caveat on the largest component:** a single merge edge is enough to join two trees. Only 10 merges connect the FLUX.1-dev tree (43,000 models) to any other root; 8 of them join it to FLUX.1-schnell, and about 3 list it next to Qwen or Llama models, which is what puts it in the same component as the language models. Component size overstates how strongly families are connected; RQ2 and RQ3 measure that.
- **Depth:** maximum 39 without merges, 151 with. Nodes at depth 10 or more: 185 without, 6,917 with. Merge models sit at mean depth 6.4.
- **Root level:** in 85.5% of merges the parents trace back to different roots.
- **Family level:** same family 6,852 (45.5%), cross-family 203 (1.3%), undetermined 7,991 (53.1%, an unknown root is involved). Among merges with known families, 2.9% are cross-family. Most common: llama + mistral (82).
- **Reading:** merges mostly join different base models of the same family, not different families. More than half of merges cannot be classified, so this is a statement about the classified half.

Family list change (Nov 12, before any result was reported): the first run counted 433 cross-family merges. 230 of them came from two wrong patterns: `bert` matched `una-cybertron-7b`, and `nemotron` labelled Llama fine-tunes as a separate family. `bert` now needs a word end, and `nemotron` was removed. The list has 41 families. The family-level result is sensitive to the list; say so in the report.

- [x] Distribution of children per model: log-binned histogram and cumulative distribution on log-log axes; exponent from the cumulative slope. Overall and per relation type.
- [x] Top-heavy share: share of edges held by the top 1%, 5%, 10% of models (Lorenz curve).
- [x] Parent-count table for merges (no fit).
- [x] Weakly connected components with and without merge edges: count, largest size, number of named families joined in one component.
- [x] Lineage depth from the topological order: distribution, with and without merges.
- [x] Share of merges that are cross-family, with and without `unknown`.

## Phase 4: RQ2, mixing (Nov 17–19)

- [ ] **Own implementation:** cocitation network of merge parents from the bipartite merge-child-to-parent table (A·Aᵀ restricted to merge edges), weighted by count. A merge with k parents adds k(k−1)/2 links.
- [ ] Family-to-family merge matrix as a heatmap.
- [ ] Family assortativity on the cocitation network with `assortativity_nominal`. Report modularity Q of the family partition next to it.
- [ ] Cocitation network versus G(n,m) with the same n and m: clustering coefficient, giant-component fraction, mean path length, each against the lecture formula and against about 100 sampled random graphs.
- [ ] **Own implementation:** inbreeding search. For a merge with parents A and B:
  - depth 0: A is an ancestor of B, or B of A (count separately);
  - depth 1–3: A and B share an ancestor within 1, 2 or 3 generations.
  - BFS along child → parent edges, capped at depth 3. Report a rate per depth.
- [ ] Repeat the main numbers with one merge counted per (author, parent set).

## Phase 5: RQ3, hubs and bridges (Nov 19–21)

- [ ] Top-20 by in-degree (children) and by PageRank on the child → parent graph, using igraph.
- [ ] Validate igraph's ranking against the Assignment 3 `PageRank.py` on a subgraph of at most 1,000 nodes.
- [ ] Betweenness on the cocitation network (small enough for the exact BFS-based algorithm of Topic 5). On the lineage graph, use `betweenness(cutoff=k)` on the undirected largest component.
- [ ] Leiden communities on the cocitation network. Compare Q with the family partition's Q; show the community-by-family table.
- [ ] Optional: HITS hub and authority scores.

## Phase 6: RQ4, reach (Nov 21–22)

- [ ] **Own implementation:** reach(v) = number of descendants of v, by BFS against the edge direction.
- [ ] Reach for every root on `G_full` and `G_nomerge`: distribution, largest reach, reach added by merges.
- [ ] Audit coverage: share of total reach covered by the top-k models by in-degree or PageRank, against k random models (random failure versus hub failure, Topic 4).

## Phase 7: Baselines (Nov 22–23)

Both baselines are degree-preserving random graphs, as the proposal says. About 100 runs each, fixed seeds.

- [ ] Mixing: degree-preserving rewiring of the cocitation graph with `rewire()`. Recompute family assortativity on each run. Report the real value against the mean and spread, as a z-score.
- [ ] Inbreeding: shuffle the parent column of the merge-child-to-parent table, so every parent keeps its merge count and every child keeps its parent count. Reject a swap that gives a child the same parent twice or a parent newer than the child. Rerun the depth 0–3 search on each run. Report z-scores.

## Phase 8: Buffer (Nov 24–25)

- [ ] Catch up. No new work.

## Phase 9: Demo (Nov 26–27)

- [ ] 10 minutes: data set, graph model, metrics, algorithms running, first findings. One slide listing the changes from the proposal (Part B).
- [ ] Slides are graded on technical content, storytelling, idea delivery and slide quality.

## Phase 10: Report and submission (Nov 28–Dec 7)

- [ ] LaTeX report, 8 pages maximum, following the six workflow steps. Limitations first: declared lineage only, so all counts are lower bounds.
- [ ] State exactly as implemented: edge direction, merge definition, family rule, inbreeding rule, reach metric, baselines.
- [ ] Zip: source code, data (filtered edge list; raw file by download script, as the proposal says), processed metric data, readme with the pinned commit and run order.
- [ ] Submit by Dec 7, 11:59 pm.

---

## Tips

- Cache the cleaned graph; do not re-parse the parquet on every run.
- Fix random seeds for random graphs, shuffles, Leiden and random removal.
- Save each metric's output to `data/processed/`; the regulation asks for processed metric data in the zip.
