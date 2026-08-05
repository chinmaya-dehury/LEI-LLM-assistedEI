#!/usr/bin/env python3
"""
monitor_all_generated_tasks.py
--------------------------------
Scan `generated_tasks/*` for Python scripts, run each script, monitor CPU/memory,
and append a summary row per script to `res_usage_code.csv` in the repository root.

Columns written to `res_usage_code.csv`:
  dataset, script_path, exit_code, duration_s, samples, avg_cpu_percent, peak_rss_mb, timestamp

Usage:
  python monitor_all_generated_tasks.py --interval 1.0 --timeout 300
"""

from __future__ import annotations

import csv
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import List

from monitor_generated_code import monitor_process


MASTER_CSV = os.path.join("result_code", "res_usage_code.csv")
try:
    os.makedirs("result_code", exist_ok=True)
    with open(MASTER_CSV, "a") as f:
        pass
except PermissionError:
    MASTER_CSV = os.path.join("result_code", "res_usage_code_updated.csv")


def find_generated_scripts(root: str = "generated_tasks") -> List[tuple]:
    """Return list of (dataset, script_path) for .py files under generated_tasks/*"""
    results = []
    if not os.path.isdir(root):
        return results
    for dataset in sorted(os.listdir(root)):
        ds_dir = os.path.join(root, dataset)
        if not os.path.isdir(ds_dir):
            continue
        # skip any dataset folder explicitly named 'failed'
        if dataset.lower() == "failed":
            continue
        for dirpath, _, files in os.walk(ds_dir):
                for f in files:
                    if f.endswith(".py"):
                        # skip __init__.py and helper modules if desired
                        if f == "__init__.py":
                            continue
                        full = os.path.join(dirpath, f)
                        # skip any path that contains a 'failed' folder
                        parts = os.path.normpath(full).split(os.sep)
                        if "failed" in [p.lower() for p in parts]:
                            continue
                        results.append((dataset, full))
    return results


def append_master_row(csv_path: str, row: dict) -> None:
    header = ["dataset", "script_path", "exit_code", "duration_s", "avg_cpu_percent", "peak_rss_mb", "timestamp"]
    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main(argv: List[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run and monitor all generated task scripts under generated_tasks/*")
    parser.add_argument("--interval", type=float, default=0.1, help="Sampling interval seconds")
    parser.add_argument("--timeout", type=float, default=300.0, help="Per-script timeout seconds (default: 300.0)")
    parser.add_argument("--root", default="generated_tasks", help="generated_tasks root folder")
    args = parser.parse_args(argv)

    scripts = find_generated_scripts(args.root)
    if not scripts:
        print("[monitor_all] No generated scripts found under", args.root)
        return 1

    for dataset, script in scripts:
        print(f"[monitor_all] Running {script} (dataset={dataset}) to completion (timeout={args.timeout}s, interval={args.interval}s, 1 run only)")
        cmd = [sys.executable, script]
        p = subprocess.Popen(cmd, cwd=os.path.dirname(script) or None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # use the monitor to collect a per-script CSV and summary
        tmp_csv = os.path.splitext(script)[0] + "_resmon.csv"
        try:
            summary = monitor_process(p, tmp_csv, interval=args.interval, timeout=args.timeout, extra_info={"dataset": dataset}, relaunch=False)
        except Exception as e:
            print(f"[monitor_all] Error monitoring {script}: {e}")
            continue

        row = {
            "dataset": dataset,
            "script_path": os.path.relpath(script),
            "exit_code": summary.get("exit_code"),
            "duration_s": summary.get("duration_s"),
            "avg_cpu_percent": summary.get("avg_cpu_percent"),
            "peak_rss_mb": summary.get("peak_rss_mb"),
            "timestamp": datetime.now().isoformat(),
        }
        append_master_row(MASTER_CSV, row)
        print(f"[monitor_all] Recorded summary for {script} -> {MASTER_CSV}")

    print("[monitor_all] All done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
