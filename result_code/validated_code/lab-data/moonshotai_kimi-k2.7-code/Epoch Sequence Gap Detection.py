"""
Task: Epoch Sequence Gap Detection
Description: For each mote, detect missing or skipped epochs by checking consecutive epoch values and reporting any gaps, supporting synchronization and data completeness analysis.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "lab-data", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "lab-data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime

TASK_NAME = "epoch_sequence_gap_detection"
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1")
MISSING_MARKERS = {"", "NA", "N/A", "None", "NULL", "None", "none"}


def find_project_root():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    return root_dir


def safe_int(value, column):
    if value is None:
        return None
    value = str(value).strip()
    if value in MISSING_MARKERS:
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        print(f"Warning: invalid integer in column '{column}': '{value}'", file=sys.stderr)
        return None


def load_data(filepath):
    rows = []
    dropped = 0
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower().strip(): v for k, v in row.items()}
            moteid = safe_int(row.get("moteid"), "moteid")
            epoch = safe_int(row.get("epoch"), "epoch")
            if moteid is None or epoch is None:
                dropped += 1
                continue
            rows.append({"moteid": moteid, "epoch": epoch})
    return rows, dropped


def detect_gaps(rows):
    mote_epochs = {}
    for r in rows:
        mote_epochs.setdefault(r["moteid"], set()).add(r["epoch"])

    results = []
    total_gaps = 0
    total_missing = 0
    for moteid in sorted(mote_epochs):
        epochs = sorted(mote_epochs[moteid])
        gaps = []
        for i in range(1, len(epochs)):
            prev = epochs[i - 1]
            curr = epochs[i]
            if curr > prev + 1:
                missing = list(range(prev + 1, curr))
                gaps.append({
                    "start_epoch": prev,
                    "end_epoch": curr,
                    "missing_count": len(missing),
                    "missing_epochs": missing
                })
                total_missing += len(missing)
        total_gaps += len(gaps)
        results.append({
            "moteid": moteid,
            "observed_epochs": len(epochs),
            "min_epoch": epochs[0] if epochs else None,
            "max_epoch": epochs[-1] if epochs else None,
            "gap_count": len(gaps),
            "gaps": gaps
        })
    return results, total_gaps, total_missing


def main():
    root_dir = find_project_root()
    data_file = root_dir / "data" / "lab-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "lab-data" / "raw_data.txt"
    if not data_file.exists():
        print(f"Error: no raw_data.csv/txt found under {root_dir / 'data' / 'lab-data'}", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {data_file}")
    rows, dropped = load_data(data_file)
    print(f"Loaded {len(rows)} valid readings, dropped {dropped} invalid rows")

    gap_results, total_gaps, total_missing = detect_gaps(rows)
    motes_with_gaps = sum(1 for r in gap_results if r["gap_count"] > 0)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{TASK_NAME}_result.json"
    result = {
        "task_name": TASK_NAME,
        "description": "Detect missing or skipped epochs per mote to assess synchronization and data completeness.",
        "result_summary": {
            "total_motes_analyzed": len(gap_results),
            "motes_with_gaps": motes_with_gaps,
            "total_gaps": total_gaps,
            "total_missing_epochs": total_missing,
            "dropped_invalid_rows": dropped,
            "mote_gap_details": gap_results
        },
        "result_generated_at": datetime.utcnow().isoformat() + "Z"
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Result saved to {output_path}")


if __name__ == "__main__":
    main()