import json
import sys
import math
import csv
"""
Task: Pest Pressure Anomaly Detection
Description: Compare current Pest_Pressure against a short-term local baseline to detect unusual spikes in pest infestation, enabling targeted intervention before thresholds are exceeded.
"""

# Programmatic path resolution pre-injected for reliability
import os
from pathlib import Path

_curr_dir = Path(__file__).resolve().parent
_root_dir = _curr_dir
while _root_dir.name and not (_root_dir / "data").exists():
    _parent = _root_dir.parent
    if _parent == _root_dir:
        break
    _root_dir = _parent

DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "agri-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "agri-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import os, csv, json, math, sys
from pathlib import Path
from datetime import datetime, timezone

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ("raw_data.csv", "raw_data.txt"):
        p = root_dir / "data" / "agri-data" / name
        if p.exists():
            return p
    return None

def to_float(v, col):
    if v is None:
        return None
    s = str(v).strip()
    if s == "" or s.upper() in ("NA", "N/A", "NULL"):
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value in column '{col}': {v!r}", file=sys.stderr)
        return None

def main():
    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv/txt not found under data/agri-data/", file=sys.stderr)
        sys.exit(1)

    rows = []
    dropped = 0
    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            try:
                row = {k.lower().strip(): v for k, v in row.items()}
                pp = to_float(row.get("pest_pressure"), "pest_pressure")
                if pp is None:
                    dropped += 1
                    continue
                rows.append({"index": i, "pest_pressure": pp})
            except Exception as e:
                print(f"Warning: row {i} skipped: {e}", file=sys.stderr)
                dropped += 1

    if not rows:
        print("Error: no valid Pest_Pressure data found.", file=sys.stderr)
        sys.exit(1)

    window = 5
    values = [r["pest_pressure"] for r in rows]
    n = len(values)
    global_mean = sum(values) / n

    results = []
    for i, r in enumerate(rows):
        if i >= window:
            baseline = sum(values[i-window:i]) / window
            mean_b = baseline
            var = sum((x - mean_b) ** 2 for x in values[i-window:i]) / window
            std = math.sqrt(var) if var > 0 else 0.0
        else:
            baseline = global_mean
            var = sum((x - global_mean) ** 2 for x in values) / n
            std = math.sqrt(var) if var > 0 else 0.0
        deviation = r["pest_pressure"] - baseline
        z = deviation / std if std > 0 else 0.0
        status = "anomaly" if (z > 2.0 or (baseline > 0 and r["pest_pressure"] > baseline * 1.25)) else "normal"
        results.append({
            "row_index": r["index"],
            "pest_pressure": round(r["pest_pressure"], 3),
            "baseline": round(baseline, 3),
            "deviation": round(deviation, 3),
            "z_score": round(z, 3),
            "status": status
        })

    anomalies = [r for r in results if r["status"] == "anomaly"]
    summary = {
        "task_name": "Pest Pressure Anomaly Detection",
        "description": "Compare current Pest_Pressure against a short-term local baseline to detect unusual spikes in pest infestation, enabling targeted intervention before thresholds are exceeded.",
        "result_summary": [
            {
                "total_rows_processed": n,
                "rows_dropped": dropped,
                "window_size": window,
                "global_mean_pest_pressure": round(global_mean, 3),
                "anomaly_count": len(anomalies),
                "anomalies": anomalies[:10],
                "latest_status": results[-1]["status"] if results else None
            }
        ],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "Pest_Pressure_Anomaly_Detection_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Pest Pressure Anomaly Detection complete: {len(anomalies)} anomalies in {n} rows. Saved to {out_file}")

if __name__ == "__main__":
    main()