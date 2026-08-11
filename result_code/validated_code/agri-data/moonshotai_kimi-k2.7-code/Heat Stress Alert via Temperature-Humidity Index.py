"""
Task: Heat Stress Alert via Temperature-Humidity Index
Description: Evaluate the Temperature-Humidity Index (THI) against safe thresholds to detect heat-stress conditions that can reduce crop performance. Generates a low/medium/high stress alert.
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

#!/usr/bin/env python3
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = "Heat Stress Alert via Temperature-Humidity Index"
DESCRIPTION = "Evaluate the Temperature-Humidity Index (THI) against safe thresholds to detect heat-stress conditions that can reduce crop performance. Generates a low/medium/high stress alert."

OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1")

MISSING_VALS = {"", "NA", "N/A", "None", "NULL", "None", "nan"}

def is_missing(v):
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s in MISSING_VALS or s.lower() == "nan"

def to_float(v, col):
    if is_missing(v):
        return None
    try:
        return float(v)
    except Exception as e:
        print(f"Warning: cannot convert {col} value {v!r} to float: {e}", file=sys.stderr)
        return None

def compute_thi(t, rh):
    # Standard Temperature-Humidity Index (comfort / heat-stress index)
    return 0.8 * t + rh * (t - 14.4) / 100.0 + 46.4

def alert_level(thi):
    if thi < 70:
        return "low"
    elif thi < 80:
        return "medium"
    return "high"

def find_data_file(root_dir):
    for name in ("raw_data.csv", "raw_data.txt"):
        p = root_dir / "data" / "agri-data" / name
        if p.exists():
            return p
    return None

def main():
    strict = "--strict" in sys.argv

    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    data_file = find_data_file(root_dir)
    if data_file is None:
        print(f"Error: input file not found under {root_dir / 'data' / 'agri-data'}", file=sys.stderr)
        sys.exit(1)

    total = 0
    valid = 0
    dropped = 0
    alert_counts = {"low": 0, "medium": 0, "high": 0}
    crop_alert_counts = {}
    alerts = []

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            total += 1
            row = {k.lower().strip(): v for k, v in row.items()}
            label = row.get("label", "unknown")
            temp = to_float(row.get("temperature"), "temperature")
            hum = to_float(row.get("humidity"), "humidity")
            thi_col = to_float(row.get("thi"), "thi")

            if temp is not None and hum is not None:
                thi = compute_thi(temp, hum)
            elif thi_col is not None:
                thi = thi_col
            else:
                print(f"Row {idx}: missing temperature/humidity and THI; skipped", file=sys.stderr)
                dropped += 1
                continue

            if math.isnan(thi):
                print(f"Row {idx}: invalid THI value; skipped", file=sys.stderr)
                dropped += 1
                continue

            valid += 1
            level = alert_level(thi)
            alert_counts[level] += 1
            crop_alert_counts.setdefault(label, {"low": 0, "medium": 0, "high": 0})
            crop_alert_counts[label][level] += 1
            alerts.append({
                "row": idx,
                "label": label,
                "temperature": temp,
                "humidity": hum,
                "thi": round(thi, 2),
                "alert": level
            })

    summary = {
        "input_file": str(data_file),
        "total_rows": total,
        "valid_rows": valid,
        "dropped_rows": dropped,
        "alert_counts": alert_counts,
        "crop_alert_counts": crop_alert_counts,
        "alerts": alerts
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{TASK_NAME}_result.json"
    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [summary],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved {out_path}")
    if strict and dropped > 0:
        sys.exit(2)

if __name__ == "__main__":
    main()