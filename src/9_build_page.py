"""Step 9: build results/index.html, a viewer for everything the steps produced.

The viewer is not a presentation. It shows, for each step, exactly what that
step wrote to its results folder:
    * key numbers, read from its summary JSON
    * its figures (the PNG files stay in the folders; the page links to them)
    * its tables (CSV files), sortable
    * every number in its summary JSON
    * its terminal output (log.txt)
plus an overview of the last run: which steps ran, how long they took, and
whether the built-in checks passed.

New files in a results folder show up automatically on the next build.
It is one static file: no server, no internet; double-click to open.

Run from the project root (MergeMap.py runs it after every run):

    python src/9_build_page.py
"""

import html
import json
from datetime import datetime
from pathlib import Path

import polars as pl
from PIL import Image

from lib.paths import RESULTS

OUT = RESULTS / "index.html"
ROWS_SHOWN = 25          # longer tables show this many rows until "Show all" is clicked
WIDE_RATIO = 1.7         # a figure at least this many times wider than tall spans the whole row

# (id, menu label, title, results folder, scripts whose status is shown)
VIEWS = [
    ("pipeline", "Pipeline", "Data and graph", "pipeline", ["1_download.py", "2_build_edges.py", "3_build_graph.py"]),
    ("rq1", "RQ1", "RQ1 · Structure", "rq1", ["4_rq1.py"]),
    ("rq2", "RQ2", "RQ2 · Mixing and inbreeding", "rq2", ["5_rq2.py"]),
    ("rq3", "RQ3", "RQ3 · Hubs and bridges", "rq3", ["6_rq3.py"]),
    ("rq4", "RQ4", "RQ4 · Reach and audit coverage", "rq4", ["7_rq4.py"]),
    ("baseline", "Baselines", "Random baselines", "baseline", ["8_baseline.py"]),
]

# Key numbers shown at the top of each view: (label, json file, path in the json, format).
# Parts of a path are separated by "/".
KEY_NUMBERS = {
    "pipeline": [
        ("Models in the snapshot", "edges_summary.json", "models", "int"),
        ("Models that declare a base model", "edges_summary.json", "models_declaring_a_base", "int"),
        ("Clean edges", "edges_summary.json", "clean_edges", "int"),
        ("Graph nodes", "graph_summary.json", "nodes", "int"),
        ("Roots", "graph_summary.json", "roots", "int"),
        ("Merges with 2+ parents", "edges_summary.json", "merges_with_2plus_parents", "int"),
        ("Deepest lineage (generations)", "graph_summary.json", "max_depth", "int"),
        ("Merge parents with unknown family", "graph_summary.json", "merge_parents_unknown", "int"),
    ],
    "rq1": [
        ("Largest component, without merges", "rq1_summary.json", "components_nomerge/largest", "int"),
        ("Largest component, with merges", "rq1_summary.json", "components_full/largest", "int"),
        ("Components, without merges", "rq1_summary.json", "components_nomerge/components", "int"),
        ("Components, with merges", "rq1_summary.json", "components_full/components", "int"),
        ("Power-law exponent (children)", "rq1_summary.json", "children/alpha_from_cumulative_slope", "f2"),
        ("Edges held by the top 0.01% of models", "rq1_summary.json", "top_heavy_share/top_0.01%/edge_share", "pct"),
        ("Merges: parents from different roots", "rq1_summary.json", "merge_mixing/cross_root_share", "pct"),
        ("Merges: cross-family (known families)", "rq1_summary.json", "merge_mixing/cross_family_share_of_determined", "pct"),
        ("Attachment exponent β (1 = preferential)", "rq1_summary.json", "growth/kernel_exponent_beta", "f2"),
        ("Largest hubs: rate vs fitted line", "rq1_summary.json", "growth/rate_largest_bins_vs_linear", "f2"),
        ("Age vs children (Spearman)", "rq1_summary.json", "growth/spearman_age_children_models_with_children", "f3"),
        ("Hubs: children gained in first 90 days", "rq1_summary.json", "growth/median_share_of_children_in_first_90_days", "pct"),
    ],
    "rq2": [
        ("Cocitation network: parents", "rq2_summary.json", "cocitation/nodes", "int"),
        ("Cocitation network: links", "rq2_summary.json", "cocitation/edges", "int"),
        ("Family assortativity, all labels", "rq2_summary.json", "mixing/all_labels_weighted/assortativity", "f3"),
        ("Family assortativity, named only", "rq2_summary.json", "mixing/named_only_weighted/assortativity", "f3"),
        ("Clustering coefficient", "rq2_summary.json", "versus_random_graph/observed/clustering", "f3"),
        ("Clustering, G(n,m) random graph", "rq2_summary.json", "versus_random_graph/gnm_sample_mean/clustering", "f4"),
        ("Inbred within 1 generation", "rq2_summary.json", "inbreeding/1/total", "pct"),
        ("Inbred at any depth", "rq2_summary.json", "inbreeding/any/total", "pct"),
        ("Copy an earlier merge's parents (J ≥ 0.5)", "rq2_summary.json", "copying/share_copying", "pct"),
        ("Exact repeat of a parent set", "rq2_summary.json", "copying/share_exact_repeat", "pct"),
        ("Copy another author's parents", "rq2_summary.json", "copying/share_copying_another_author", "pct"),
        ("Copies made by the same author", "rq2_summary.json", "copying/copies_by_same_author", "pct"),
    ],
    "rq3": [
        ("PageRank vs matrix inverse, largest difference", "rq3_summary.json", "pagerank_checks/matrix_inverse_largest_difference", "sci"),
        ("Rank correlation, children vs PageRank", "rq3_summary.json", "hubs/spearman_children_pagerank_among_parents", "f3"),
        ("Top-20 overlap, children vs PageRank", "rq3_summary.json", "hubs/overlap_top20_children_pagerank", "int"),
        ("Merges among the top 100 bridges", "rq3_summary.json", "lineage_betweenness/merge_share_of_top/100", "pct"),
        ("Betweenness held by merges", "rq3_summary.json", "lineage_betweenness/share_of_total_betweenness_held_by_merges", "pct"),
        ("Leiden communities (best of runs)", "rq3_summary.json", "communities/best_run/communities", "int"),
        ("Modularity Q, Leiden", "rq3_summary.json", "communities/best_run/modularity", "f3"),
        ("Modularity Q, family labels", "rq3_summary.json", "communities/modularity_family_labels", "f3"),
    ],
    "rq4": [
        ("Root–descendant pairs, without merges", "rq4_summary.json", "root_reach/total_without_merges", "int"),
        ("Root–descendant pairs, with merges", "rq4_summary.json", "root_reach/total_with_merges", "int"),
        ("Added by merges", "rq4_summary.json", "root_reach/added_share", "pct"),
        ("Roots that gain through merges", "rq4_summary.json", "root_reach/roots_that_gain", "int"),
        ("Models with 2+ roots", "rq4_summary.json", "multi_root_exposure/models_with_2plus_roots", "int"),
        ("Most roots behind one model", "rq4_summary.json", "multi_root_exposure/max_roots_of_one_model", "int"),
        ("Coverage, top 100 by PageRank", "rq4_summary.json", "audit_coverage/by PageRank/100", "pct"),
        ("Coverage, 100 random models with a child", "rq4_summary.json", "audit_coverage/random models with a child/100", "pct"),
    ],
    "baseline": [
        ("Inbred within 1, observed", "baseline_summary.json", "inbreeding/1/total/observed", "pct"),
        ("Inbred within 1, shuffled within families", "baseline_summary.json", "inbreeding_within_family/1/total/baseline_mean", "pct"),
        ("Inbred within 1, shuffled merges", "baseline_summary.json", "inbreeding/1/total/baseline_mean", "pct"),
        ("z-score, within families", "baseline_summary.json", "inbreeding_within_family/1/total/z", "f1"),
        ("Assortativity, observed", "baseline_summary.json", "mixing_shuffled_merges/all_labels_unweighted/observed", "f3"),
        ("Assortativity, shuffled merges", "baseline_summary.json", "mixing_shuffled_merges/all_labels_unweighted/baseline_mean", "f3"),
        ("Assortativity, rewired cocitation", "baseline_summary.json", "rewired_cocitation/assortativity_all_labels_unweighted/baseline_mean", "f3"),
        ("Runs per baseline", "baseline_summary.json", "runs", "int"),
        ("Copying, observed", "baseline_summary.json", "copying_within_family/share_copying/observed", "pct"),
        ("Copying, shuffled within families", "baseline_summary.json", "copying_within_family/share_copying/baseline_mean", "pct"),
        ("Exact repeats, observed", "baseline_summary.json", "copying_within_family/share_exact_repeat/observed", "pct"),
        ("Exact repeats, shuffled within families", "baseline_summary.json", "copying_within_family/share_exact_repeat/baseline_mean", "pct"),
    ],
}


def esc(text):
    return html.escape(str(text), quote=True)


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def lookup(data, path):
    """Follow a path such as 'a/b/c' into nested dicts."""
    node = data
    for part in path.split("/"):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def fmt(value, kind):
    if value is None:
        return "—"
    if kind == "int":
        return f"{int(value):,}"
    if kind == "pct":
        return f"{100 * value:.1f}%"
    if kind == "sci":
        return f"{value:.1e}"
    return f"{value:.{int(kind[1])}f}"          # f1, f2, f3, f4


def pretty(name):
    """'rq1_children_by_relation.png' -> 'Children by relation'."""
    stem = Path(name).stem
    for prefix in ("rq1_", "rq2_", "rq3_", "rq4_", "baseline_", "log_"):
        if stem.startswith(prefix):
            stem = stem[len(prefix):]
    stem = stem.replace("_", " ")
    return stem[:1].upper() + stem[1:]


def cell(value):
    if value is None:
        return "", ""
    if isinstance(value, bool):
        return str(value), str(value)
    if isinstance(value, int):
        return f"{value:,}", value
    if isinstance(value, float):
        if value != 0 and (abs(value) < 1e-3 or abs(value) >= 1e6):
            return f"{value:.3e}", value
        return (f"{value:,.0f}" if abs(value) >= 1000 else f"{value:.4g}"), value
    return esc(value), esc(value)


def csv_table(path):
    df = pl.read_csv(path, infer_schema_length=10000)
    numeric = {c for c, t in df.schema.items() if t.is_numeric()}
    head = "".join(f'<th data-kind="{"num" if c in numeric else "text"}" class="{"num" if c in numeric else ""}" '
                   f'tabindex="0">{esc(c)}</th>' for c in df.columns)
    rows = []
    for i, row in enumerate(df.iter_rows()):
        cells = []
        for c, value in zip(df.columns, row):
            shown, sort = cell(value)
            cls = "num" if c in numeric else ("name" if isinstance(value, str) and "/" in value else "")
            cells.append(f'<td class="{cls}" data-v="{sort}">{shown}</td>')
        rows.append(f'<tr{" class=extra" if i >= ROWS_SHOWN else ""}>{"".join(cells)}</tr>')
    more = ""
    if df.height > ROWS_SHOWN:
        more = f'<button class="more" type="button">Show all {df.height:,} rows</button>'
    return (f'<div class="table-wrap"><table class="sortable collapsed"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>{more}'
            f'<div class="file-note">{df.height:,} rows · {esc(path.as_posix())}</div>')


def flatten(data, path=""):
    """Every number in a summary JSON as (path, shown value) rows."""
    if isinstance(data, dict):
        rows = []
        for key, value in data.items():
            rows += flatten(value, f"{path} › {key}" if path else str(key))
        return rows
    if isinstance(data, list):
        shown = esc(json.dumps(data, ensure_ascii=False))
        return [(path, shown if len(shown) <= 160 else shown[:157] + "…")]
    return [(path, cell(data)[0])]


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------
run_info = read_json(RESULTS / "run_info.json") or {"steps": []}
step_info = {s["script"]: s for s in run_info.get("steps", [])}
snapshot = read_json(RESULTS / "pipeline" / "snapshot.json") or {}
edges_s = read_json(RESULTS / "pipeline" / "edges_summary.json") or {}
graph_s = read_json(RESULTS / "pipeline" / "graph_summary.json") or {}
rq2 = read_json(RESULTS / "rq2" / "rq2_summary.json") or {}
rq3 = read_json(RESULTS / "rq3" / "rq3_summary.json") or {}
rq4 = read_json(RESULTS / "rq4" / "rq4_summary.json") or {}


def status_of(scripts):
    states = [step_info.get(s, {}).get("status", "not run") for s in scripts]
    if "failed" in states:
        return "failed"
    if all(s == "ok" for s in states):
        return "ok"
    if all(s in ("ok", "reused") for s in states):
        return "reused"
    return "not run"


def seconds_of(scripts):
    values = [step_info.get(s, {}).get("seconds") for s in scripts]
    return sum(v for v in values if v) if any(values) else None


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
def check(label, ok, note):
    return (f'<li class="{"pass" if ok else "fail"}"><span class="mark">{"✓" if ok else "✗"}</span>'
            f'<span>{esc(label)}</span><span class="check-note">{esc(note)}</span></li>')


pr = rq3.get("pagerank_checks", {})
mix = rq2.get("mixing", {})
checks = [
    check("Data snapshot matches the pinned commit", snapshot.get("sha256_matches", False),
          f'{snapshot.get("revision", "")[:10]} · SHA-256 {snapshot.get("sha256", "")[:12]}…'),
    check("Lineage graph is acyclic", graph_s.get("is_dag", False) and graph_s.get("cycles_found", 1) == 0,
          f'{graph_s.get("cycles_found", "?")} cycles'),
    check("Without merges, no model has two parents", edges_s.get("non_merge_models_with_2plus_parents", 1) == 0,
          f'{edges_s.get("non_merge_models_with_2plus_parents", "?")} exceptions'),
    check("PageRank equals the Assignment 3 matrix inverse", pr.get("matrix_inverse_largest_difference", 1) < 1e-8,
          f'largest difference {pr.get("matrix_inverse_largest_difference", float("nan")):.1e}'),
    check("PageRank is proportional to igraph's", pr.get("igraph_ratio_relative_spread", 1) < 1e-8,
          f'spread {pr.get("igraph_ratio_relative_spread", float("nan")):.1e}'),
    check("Assortativity equals igraph's",
          abs(lookup(mix, "all_labels_unweighted/assortativity") or 0) > 0 and
          abs((lookup(mix, "all_labels_unweighted/assortativity") or 0)
              - (lookup(mix, "igraph_check_unweighted/assortativity") or 9)) < 1e-9,
          f'r = {lookup(mix, "all_labels_unweighted/assortativity") or float("nan"):.4f}'),
    check("Reach by BFS agrees with the root sets", rq4.get("check_root_reach_matches_root_sets", False),
          f'{lookup(rq4, "root_reach/total_with_merges") or 0:,} pairs'),
]

steps = run_info.get("steps", [])
total = sum(s.get("seconds") or 0 for s in steps if s.get("status") == "ok")
max_s = max([s.get("seconds") or 0 for s in steps] + [1])
def step_row(s):
    seconds = s.get("seconds")
    time_text = "" if seconds is None else f"{seconds:.0f} s"
    return (f'<tr><td><code>{esc(s["script"])}</code></td><td>{esc(s.get("description", ""))}</td>'
            f'<td><span class="pill {esc(s["status"])}">{esc(s["status"])}</span></td>'
            f'<td class="num">{time_text}</td><td class="bar-cell"><span class="bar {esc(s["status"])}" '
            f'style="width:{100 * (seconds or 0) / max_s:.1f}%"></span></td></tr>')


step_rows = "".join(step_row(s) for s in steps)

overview = f"""
<div class="view-head"><div><div class="crumb">Overview</div><h1>Last run</h1></div>
  <div class="head-meta">{esc(run_info.get("finished", "never").replace("T", " "))} · {esc(run_info.get("mode", ""))} mode
  · {total:.0f} s · Python {esc(run_info.get("python", ""))}</div></div>
<div class="grid-2">
  <div class="card"><h2>Steps</h2><div class="table-wrap"><table class="steps">
    <thead><tr><th>Script</th><th>What it does</th><th>Status</th><th class="num">Time</th><th></th></tr></thead>
    <tbody>{step_rows or '<tr><td colspan="5">No run recorded yet. Run <code>python MergeMap.py</code>.</td></tr>'}</tbody></table></div>
    <p class="file-note">“reused” = skipped by <code>--quick</code>; its results come from the last full run.</p></div>
  <div class="card"><h2>Built-in checks</h2><ul class="checks">{"".join(checks)}</ul></div>
</div>
<div class="card"><h2>Data snapshot</h2><div class="kv">
  <span>Dataset</span><b>{esc(snapshot.get("repo_id", "—"))} / {esc(snapshot.get("file", ""))}</b>
  <span>Commit</span><b><code>{esc(snapshot.get("revision", "—"))}</code></b>
  <span>Uploaded</span><b>{esc(snapshot.get("uploaded", "—"))}</b>
  <span>Size</span><b>{snapshot.get("bytes", 0):,} bytes</b>
  <span>Licence</span><b>{esc(snapshot.get("licence", "—"))}</b>
</div></div>"""


# ---------------------------------------------------------------------------
# One view per results folder
# ---------------------------------------------------------------------------
def build_view(vid, title, folder_name, scripts):
    folder = RESULTS / folder_name
    files = sorted(folder.glob("*")) if folder.exists() else []
    jsons = {f.name: read_json(f) for f in files if f.suffix == ".json"}
    figures = [f for f in files if f.suffix == ".png"]
    tables = [f for f in files if f.suffix == ".csv"]
    logs = [f for f in files if f.suffix == ".txt"]
    data_files = [f for f in files if f.suffix == ".parquet"]

    keys = "".join(
        f'<div class="metric"><b>{fmt(lookup(jsons.get(file), path), kind)}</b><span>{esc(label)}</span></div>'
        for label, file, path, kind in KEY_NUMBERS.get(vid, []))

    def is_wide(png):
        """Two-panel figures (much wider than tall) get a full row of their own."""
        with Image.open(png) as im:
            width, height = im.size
        return width / height >= WIDE_RATIO

    # Wide figures first, then the rest in pairs, so every row is evenly filled.
    figures = sorted(figures, key=lambda f: (not is_wide(f), f.name))
    fig_html = "".join(
        f'<figure class="fig{" wide" if is_wide(f) else ""}"><button class="zoom" type="button" '
        f'aria-label="Enlarge {esc(pretty(f.name))}">'
        f'<img src="{esc(folder_name)}/{esc(f.name)}" alt="{esc(pretty(f.name))}" loading="lazy"></button>'
        f'<figcaption><b>{esc(pretty(f.name))}</b><span>{esc((folder / f.name).as_posix())}</span></figcaption></figure>'
        for f in figures)

    tab_buttons = "".join(f'<button type="button" role="tab" aria-selected="{str(i == 0).lower()}" '
                          f'data-tab="{vid}-t{i}">{esc(pretty(f.name))}</button>' for i, f in enumerate(tables))
    tab_panels = "".join(f'<div class="tab-panel" id="{vid}-t{i}"{"" if i == 0 else " hidden"}>{csv_table(f)}</div>'
                         for i, f in enumerate(tables))

    numbers = "".join(
        f'<details class="json"><summary>{esc(name)}</summary><table class="kvtable"><tbody>'
        + "".join(f"<tr><td>{esc(k)}</td><td class='num'>{v}</td></tr>" for k, v in flatten(data or {}))
        + "</tbody></table></details>"
        for name, data in jsons.items())

    log_html = "".join(
        f'<details class="log"{" open" if len(logs) == 1 else ""}><summary>{esc(f.name)}</summary>'
        f'<pre>{esc(f.read_text(encoding="utf-8", errors="replace"))}</pre></details>' for f in logs)

    data_html = "".join(f'<li><code>{esc((folder / f.name).as_posix())}</code> · {f.stat().st_size / 1e6:.1f} MB</li>'
                        for f in data_files)

    status = status_of(scripts)
    seconds = seconds_of(scripts)
    parts = [f'<div class="view-head"><div><div class="crumb">{esc(" · ".join(scripts))}</div><h1>{esc(title)}</h1></div>'
             f'<div class="head-meta"><span class="pill {status}">{status}</span>'
             f'{"" if seconds is None else f" {seconds:.0f} s"} · <code>results/{esc(folder_name)}/</code></div></div>']
    if keys:
        parts.append(f'<div class="metrics">{keys}</div>')
    if fig_html:
        parts.append(f'<div class="card"><h2>Figures <span class="count">{len(figures)}</span></h2><div class="figs">{fig_html}</div></div>')
    if tables:
        parts.append(f'<div class="card" data-tabs><h2>Tables <span class="count">{len(tables)}</span></h2>'
                     f'<div class="tab-buttons" role="tablist">{tab_buttons}</div>{tab_panels}'
                     f'<p class="file-note">Click a column header to sort.</p></div>')
    if numbers:
        parts.append(f'<div class="card"><h2>All numbers</h2>{numbers}</div>')
    if log_html:
        parts.append(f'<div class="card"><h2>Terminal output</h2>{log_html}</div>')
    if data_html:
        parts.append(f'<div class="card"><h2>Data files</h2><ul class="files">{data_html}</ul></div>')
    return "".join(parts), status, seconds


views_html = [f'<section class="view" id="overview">{overview}</section>']
nav = ['<a href="#overview" data-view="overview"><span class="dot ok"></span>Overview</a>']
for vid, label, title, folder_name, scripts in VIEWS:
    content, status, seconds = build_view(vid, title, folder_name, scripts)
    views_html.append(f'<section class="view" id="{vid}" hidden>{content}</section>')
    nav.append(f'<a href="#{vid}" data-view="{vid}"><span class="dot {status}"></span>{esc(label)}'
               f'<em>{"" if seconds is None else f"{seconds:.0f} s"}</em></a>')

CSS = r"""
:root{--bg:#f4f3ef;--surface:#fff;--surface-2:#f9f8f5;--ink:#141413;--ink-2:#55544f;--muted:#8a8882;--line:#e4e2da;
--accent:#2a78d6;--accent-soft:#e8f1fc;--ok:#0c8a3e;--ok-soft:#e3f4e9;--warn:#a26a00;--warn-soft:#fbf0d9;--bad:#c93434;--bad-soft:#fbe4e4;--code:#1e1e1c}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#111110;--surface:#1a1a19;--surface-2:#20201f;--ink:#efeee9;--ink-2:#c2c1b8;--muted:#8d8b84;
--line:#2d2d2a;--accent:#5598e7;--accent-soft:#1a2a3d;--ok:#3cc26c;--ok-soft:#163222;--warn:#e0a83a;--warn-soft:#3a2d12;--bad:#ef6a6a;--bad-soft:#3a1c1c;--code:#0c0c0b}}
:root[data-theme="dark"]{--bg:#111110;--surface:#1a1a19;--surface-2:#20201f;--ink:#efeee9;--ink-2:#c2c1b8;--muted:#8d8b84;--line:#2d2d2a;
--accent:#5598e7;--accent-soft:#1a2a3d;--ok:#3cc26c;--ok-soft:#163222;--warn:#e0a83a;--warn-soft:#3a2d12;--bad:#ef6a6a;--bad-soft:#3a1c1c;--code:#0c0c0b}
*{box-sizing:border-box}
html{font-size:clamp(15px,calc(0.45vw + 9px),22px)}
body{margin:0;background:var(--bg);color:var(--ink);font:0.9062rem/1.55 ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;font-variant-numeric:tabular-nums}
code{font:0.7812rem ui-monospace,SFMono-Regular,Consolas,monospace}
.layout{display:grid;grid-template-columns:13.75rem minmax(0,1fr);min-height:100vh}
.side{position:sticky;top:0;height:100vh;background:var(--surface);border-right:1px solid var(--line);padding:1.375rem 0.875rem;display:flex;flex-direction:column;gap:1.125rem}
.brand{display:flex;align-items:center;gap:0.625rem;font-weight:700;font-size:1.0625rem;padding:0 0.375rem}.brand svg{width:1.75rem;height:1.75rem}
.brand small{display:block;font-weight:500;font-size:0.7188rem;color:var(--muted)}
.side nav{display:flex;flex-direction:column;gap:0.125rem}
.side nav a{display:flex;align-items:center;gap:0.625rem;padding:0.5rem 0.625rem;border-radius:0.5rem;color:var(--ink-2);text-decoration:none}
.side nav a em{margin-left:auto;font-style:normal;font-size:0.75rem;color:var(--muted)}
.side nav a:hover{background:var(--surface-2);color:var(--ink)}.side nav a.active{background:var(--accent-soft);color:var(--accent);font-weight:600}
.dot{width:0.5rem;height:0.5rem;border-radius:50%;background:var(--muted);flex:none}.dot.ok{background:var(--ok)}.dot.reused{background:var(--warn)}.dot.failed{background:var(--bad)}
.side-foot{margin-top:auto;display:flex;flex-direction:column;gap:0.5rem;font-size:0.75rem;color:var(--muted);padding:0 0.375rem}
.theme{border:1px solid var(--line);background:var(--surface-2);color:var(--ink-2);border-radius:0.5rem;padding:0.4375rem 0.625rem;font:inherit;font-size:0.8125rem;cursor:pointer}
main{margin:0 auto;padding:1.625rem 2.125rem 3.125rem;max-width:110rem;width:100%;min-width:0}
.view-head{display:flex;justify-content:space-between;align-items:flex-end;gap:1rem;flex-wrap:wrap;margin-bottom:1.125rem}
.crumb{font:0.75rem ui-monospace,Consolas,monospace;color:var(--muted)}
h1{font-size:1.625rem;letter-spacing:-.02em;margin:0.125rem 0 0}
.head-meta{font-size:0.8125rem;color:var(--ink-2);display:flex;align-items:center;gap:0.375rem;flex-wrap:wrap}
h2{font-size:0.875rem;margin:0 0 0.75rem;display:flex;align-items:center;gap:0.5rem}
.count{font-size:0.7188rem;font-weight:600;color:var(--muted);background:var(--surface-2);border:1px solid var(--line);border-radius:62.4375rem;padding:0 0.4375rem}
.card{min-width:0;background:var(--surface);border:1px solid var(--line);border-radius:0.75rem;padding:1rem 1.125rem;margin-bottom:0.875rem}
.grid-2{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);gap:0.875rem}.grid-2 .card{margin-bottom:0.875rem}
.pill{display:inline-block;font-size:0.7188rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;padding:1px 0.5rem;border-radius:62.4375rem;background:var(--surface-2);color:var(--muted)}
.pill.ok{background:var(--ok-soft);color:var(--ok)}.pill.reused{background:var(--warn-soft);color:var(--warn)}.pill.failed{background:var(--bad-soft);color:var(--bad)}
.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0.625rem;margin-bottom:0.875rem}
.metric{background:var(--surface);border:1px solid var(--line);border-radius:0.75rem;padding:0.75rem 0.875rem}
.metric b{display:block;font-size:1.3125rem;letter-spacing:-.01em}.metric span{font-size:0.75rem;color:var(--muted)}
.figs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0.75rem}
.fig{margin:0;border:1px solid var(--line);border-radius:0.625rem;overflow:hidden;background:var(--surface-2);display:flex;flex-direction:column}
.fig.wide{grid-column:1/-1}
.zoom{all:unset;display:block;cursor:zoom-in;background:#fff}.zoom:focus-visible{outline:0.125rem solid var(--accent)}
.fig img{display:block;width:100%;aspect-ratio:4/3;object-fit:contain;background:#fff}
.fig.wide img{aspect-ratio:auto;max-height:32.5rem}
figcaption{display:flex;flex-direction:column;gap:1px;padding:0.5rem 0.625rem;font-size:0.7812rem}figcaption span{color:var(--muted);font-family:ui-monospace,Consolas,monospace;font-size:0.7188rem;word-break:break-all}
.tab-buttons{display:flex;gap:0.125rem;border-bottom:1px solid var(--line);margin:0 -1.125rem 0.5rem;padding:0 0.875rem;overflow-x:auto}
.tab-buttons button{all:unset;cursor:pointer;padding:0.5rem 0.625rem;font-size:0.8125rem;color:var(--ink-2);border-bottom:0.125rem solid transparent;white-space:nowrap}
.tab-buttons button[aria-selected="true"]{color:var(--accent);border-bottom-color:var(--accent);font-weight:600}
.table-wrap{overflow-x:auto;max-height:35rem;overflow-y:auto;border:1px solid var(--line);border-radius:0.5rem}
table{border-collapse:collapse;width:100%;font-size:0.8125rem}
th{position:sticky;top:0;background:var(--surface-2);text-align:left;font-size:0.7188rem;color:var(--muted);font-weight:700;padding:0.4375rem 0.625rem;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:0.375rem 0.625rem;border-bottom:1px solid var(--line);vertical-align:top}
.num{text-align:right;white-space:nowrap}td.name{font-family:ui-monospace,Consolas,monospace;font-size:0.75rem;word-break:break-all}
tbody tr:hover td{background:var(--surface-2)}
.sortable th{cursor:pointer;user-select:none}.sortable th[aria-sort="ascending"]::after{content:" ▲"}.sortable th[aria-sort="descending"]::after{content:" ▼"}
table.collapsed tr.extra{display:none}
.more{margin-top:0.5rem;border:1px solid var(--line);background:var(--surface-2);color:var(--accent);border-radius:0.5rem;padding:0.375rem 0.75rem;font:inherit;font-size:0.8125rem;cursor:pointer}
.file-note{font-size:0.75rem;color:var(--muted);margin:0.5rem 0 0}
details{border:1px solid var(--line);border-radius:0.5rem;margin-bottom:0.5rem;background:var(--surface-2)}
summary{cursor:pointer;padding:0.5rem 0.75rem;font:0.8125rem ui-monospace,Consolas,monospace;color:var(--ink-2)}
details[open] summary{border-bottom:1px solid var(--line)}
.log pre{margin:0;padding:0.75rem 0.875rem;max-height:28.75rem;overflow:auto;background:var(--code);color:#e6e5df;font:0.7812rem/1.5 ui-monospace,Consolas,monospace;border-radius:0 0 0.5rem 0.5rem}
.kvtable td{font-size:0.7812rem}.kvtable td:first-child{color:var(--ink-2);font-family:ui-monospace,Consolas,monospace;font-size:0.75rem}
.steps td{white-space:nowrap}.bar-cell{width:30%}.bar{display:block;height:0.5rem;border-radius:62.4375rem;background:var(--accent);min-width:0.125rem}
.bar.reused{background:var(--warn);opacity:.5}.bar.failed{background:var(--bad)}
.checks{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:0.5625rem}
.checks li{display:grid;grid-template-columns:1.375rem 1fr;column-gap:0.625rem;font-size:0.8438rem}
.mark{grid-row:span 2;width:1.25rem;height:1.25rem;border-radius:50%;display:grid;place-items:center;font-size:0.6875rem;font-weight:800;color:#fff;background:var(--ok)}
.fail .mark{background:var(--bad)}.check-note{font-size:0.75rem;color:var(--muted)}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:0.375rem 1.125rem;font-size:0.8438rem}.kv span{color:var(--muted)}.kv b{font-weight:600;word-break:break-all}
.files{margin:0;padding-left:1.125rem;font-size:0.8125rem}
.lightbox{position:fixed;inset:0;background:rgba(10,10,10,.85);display:none;align-items:center;justify-content:center;padding:1.5rem;z-index:50;cursor:zoom-out}
.lightbox.open{display:flex}.lightbox img{max-width:96vw;max-height:92vh;background:#fff;border-radius:0.5rem}
@media (max-width:1050px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.grid-2{grid-template-columns:1fr}}
@media (max-width:820px){.layout{grid-template-columns:minmax(0,1fr)}.side{position:sticky;top:0;height:auto;z-index:5;flex-direction:row;align-items:center;padding:0.5rem 0.75rem;border-right:0;border-bottom:1px solid var(--line);overflow-x:auto}
.side nav{flex-direction:row}.side nav a em,.side-foot span{display:none}.side-foot{margin:0}main{padding:1.125rem 1rem 2.5rem}.figs{grid-template-columns:1fr}}
"""

JS = r"""
(function(){
  var root=document.documentElement, btn=document.getElementById('theme');
  function stored(){try{return localStorage.getItem('mm-theme')}catch(e){return null}}
  function isDark(){var t=root.getAttribute('data-theme');return t?t==='dark':matchMedia('(prefers-color-scheme: dark)').matches}
  function apply(t){if(t)root.setAttribute('data-theme',t);else root.removeAttribute('data-theme');btn.textContent=isDark()?'☀ Light theme':'☾ Dark theme'}
  apply(stored());
  btn.addEventListener('click',function(){var t=isDark()?'light':'dark';apply(t);try{localStorage.setItem('mm-theme',t)}catch(e){}});

  var views=[].slice.call(document.querySelectorAll('.view')), links=[].slice.call(document.querySelectorAll('[data-view]'));
  function show(){var id=(location.hash||'#overview').slice(1);if(!document.getElementById(id))id='overview';
    views.forEach(function(v){v.hidden=v.id!==id});links.forEach(function(a){a.classList.toggle('active',a.dataset.view===id)});window.scrollTo(0,0)}
  window.addEventListener('hashchange',show);show();

  var box=document.getElementById('lightbox'),big=box.querySelector('img');
  document.querySelectorAll('.zoom').forEach(function(b){b.addEventListener('click',function(){var i=b.querySelector('img');big.src=i.src;big.alt=i.alt;box.classList.add('open')})});
  box.addEventListener('click',function(){box.classList.remove('open')});
  document.addEventListener('keydown',function(e){if(e.key==='Escape')box.classList.remove('open')});

  document.querySelectorAll('table.sortable').forEach(function(t){var ths=[].slice.call(t.querySelectorAll('th'));
    ths.forEach(function(th,i){function sort(){var asc=th.getAttribute('aria-sort')!=='ascending';ths.forEach(function(h){h.removeAttribute('aria-sort')});
      th.setAttribute('aria-sort',asc?'ascending':'descending');var num=th.dataset.kind==='num',body=t.tBodies[0],rows=[].slice.call(body.rows);
      rows.sort(function(a,b){var x=a.cells[i].dataset.v,y=b.cells[i].dataset.v;if(num){x=parseFloat(x);y=parseFloat(y);if(isNaN(x))x=-Infinity;if(isNaN(y))y=-Infinity;return asc?x-y:y-x}return asc?x.localeCompare(y):y.localeCompare(x)});
      rows.forEach(function(r,k){r.classList.toggle('extra',k>=25);body.appendChild(r)})}
      th.addEventListener('click',sort);th.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();sort()}})})});
  document.querySelectorAll('.more').forEach(function(b){b.addEventListener('click',function(){var t=b.previousElementSibling.querySelector('table');
    var open=t.classList.toggle('collapsed');b.textContent=open?b.dataset.label:'Show fewer rows'});b.dataset.label=b.textContent});

  document.querySelectorAll('[data-tabs]').forEach(function(w){var bs=[].slice.call(w.querySelectorAll('[data-tab]'));
    bs.forEach(function(b){b.addEventListener('click',function(){bs.forEach(function(x){x.setAttribute('aria-selected',x===b);document.getElementById(x.dataset.tab).hidden=x!==b})})})});
})();
"""

LOGO = ('<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M6 5 C6 15, 16 13, 16 21 M26 5 C26 15, 16 13, 16 21 M16 21 L16 28" '
        'fill="none" stroke="#2a78d6" stroke-width="3.2" stroke-linecap="round"/><circle cx="6" cy="5" r="3" fill="#2a78d6"/>'
        '<circle cx="26" cy="5" r="3" fill="#eb6834"/><circle cx="16" cy="28" r="3" fill="#1baf7a"/></svg>')

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MergeMap Results</title>
<link rel="icon" href="data:image/svg+xml,{LOGO.replace('"', "'").replace('#', '%23')}">
<style>{CSS}</style>
</head>
<body>
<div class="layout">
  <aside class="side">
    <div class="brand">{LOGO}<div>MergeMap<small>results viewer</small></div></div>
    <nav aria-label="Steps">{"".join(nav)}</nav>
    <div class="side-foot"><button class="theme" id="theme" type="button">☾ Dark theme</button>
      <span>Built {esc(datetime.now().strftime("%d %b %Y, %H:%M"))}</span></div>
  </aside>
  <main>{"".join(views_html)}</main>
</div>
<div class="lightbox" id="lightbox" role="dialog" aria-label="Enlarged figure"><img alt=""></div>
<script>{JS}</script>
</body>
</html>
"""

OUT.write_text(page, encoding="utf-8")
print(f"saved {OUT.as_posix()} ({OUT.stat().st_size / 1e3:.0f} kB)")
