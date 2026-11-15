"""MergeMap: run the whole project, then build the results page.

Usage (from the project folder, with the venv active):

    python MergeMap.py             run every step (about 15 minutes)
    python MergeMap.py --quick     skip the two slow steps if their results
                                   already exist (about 1 minute)
    python MergeMap.py --page      only rebuild results/index.html

Every step's printout is shown here and also saved to results/<step>/log.txt.
The run stops at the first step that fails and says which one it was.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# (script, results folder, short description, slow?)
STEPS = [
    ("1_download.py", "pipeline", "check the pinned data snapshot", False),
    ("2_build_edges.py", "pipeline", "build the node table and clean the edges", False),
    ("3_build_graph.py", "pipeline", "build the lineage graph and family labels", False),
    ("4_rq1.py", "rq1", "RQ1 structure", False),
    ("5_rq2.py", "rq2", "RQ2 mixing and inbreeding", True),
    ("6_rq3.py", "rq3", "RQ3 hubs and bridges", False),
    ("7_rq4.py", "rq4", "RQ4 reach and audit coverage", False),
    ("8_baseline.py", "baseline", "random baselines", True),
]
PAGE_STEP = ("9_build_page.py", ".", "build the results page", False)


def run_step(script, folder, description, log_name):
    """Run one script, show its output live, and save it to a log file."""
    log_dir = ROOT / "results" / folder
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_name
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    print(f"\n=== {script}: {description}")
    start = time.time()
    with open(log_path, "w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [sys.executable, f"src/{script}"], cwd=ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        )
        for line in process.stdout:
            sys.stdout.write("    " + line)
            log.write(line)
        process.wait()
    seconds = time.time() - start
    return process.returncode, seconds


def main():
    # Some model names and table borders cannot be shown by the Windows console;
    # show "?" for those characters instead of crashing. The log files keep them.
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Run the MergeMap project.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--quick", action="store_true",
                       help="skip 5_rq2.py and 8_baseline.py when their results already exist")
    group.add_argument("--page", action="store_true", help="only rebuild results/index.html")
    args = parser.parse_args()

    mode = "page only" if args.page else "quick" if args.quick else "full"
    info_path = ROOT / "results" / "run_info.json"
    previous = json.loads(info_path.read_text(encoding="utf-8")) if info_path.exists() else {}
    previous_steps = {s["script"]: s for s in previous.get("steps", [])}

    steps_done = []
    started = datetime.now()
    if not args.page:
        for script, folder, description, slow in STEPS:
            summary = ROOT / "results" / folder / f"{folder}_summary.json"
            if args.quick and slow and summary.exists():
                print(f"\n=== {script}: skipped in quick mode, reusing results from the last full run")
                old = previous_steps.get(script, {})
                steps_done.append({"script": script, "description": description, "status": "reused",
                                   "seconds": old.get("seconds"), "ran_at": old.get("ran_at")})
                continue
            log_name = "log.txt" if folder != "pipeline" else f"log_{script[:-3]}.txt"
            code, seconds = run_step(script, folder, description, log_name)
            steps_done.append({"script": script, "description": description,
                               "status": "ok" if code == 0 else "failed",
                               "seconds": round(seconds, 1), "ran_at": datetime.now().isoformat(timespec="seconds")})
            if code != 0:
                print(f"\n*** {script} failed (exit code {code}). See results/{folder}/{log_name}.")
                save_info(info_path, started, mode, steps_done)
                sys.exit(code)
            print(f"    done in {seconds:.0f} s")
        save_info(info_path, started, mode, steps_done)

    code, seconds = run_step(*PAGE_STEP[:3], log_name="log_page.txt")
    if code != 0:
        print("\n*** building the results page failed. See results/log_page.txt.")
        sys.exit(code)
    page = ROOT / "results" / "index.html"
    total = sum(s["seconds"] or 0 for s in steps_done if s["status"] == "ok") + seconds
    print(f"\nAll done in {total:.0f} s. Open the results page:\n    {page}")


def save_info(path, started, mode, steps):
    info = {
        "started": started.isoformat(timespec="seconds"),
        "finished": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "python": sys.version.split()[0],
        "steps": steps,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(info, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
