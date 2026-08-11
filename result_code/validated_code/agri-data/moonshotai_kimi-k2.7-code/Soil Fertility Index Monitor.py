"""
Task: Soil Fertility Index Monitor
Description: Evaluate the Soil Fertility Index (SFI) against low, medium, and high thresholds and flag fields that require soil amendment or organic matter adjustment.
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
"""Soil Fertility Index Monitor for agri-data edge device."""
import csv
import json
from pathlib import Path
from datetime import datetime, timezone


def find_data_file():
    """Locate raw_data.csv or raw_data.txt under data/agri-data/."""
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    for fname in ("raw_data.csv", "raw_data.txt"):
        data_file = root_dir / "data" / "agri-data" / fname
        if data_file.exists():
            return data_file
    return None


def safe_float(value, col_name):
    """Convert a raw value to float, treating missing/invalid as None."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.upper() in ("NA", "N/A", "NULL"):
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value '{value}' in column '{col_name}', skipping.")
        return None


def classify_sfi(sfi):
    """Classify SFI into fertility levels."""
    if sfi is None:
        return "unknown"
    if sfi < 0.65:
        return "low"
    if sfi < 0.75:
        return "medium"
    return "high"


def recommendation(level):
    """Return a short amendment recommendation per fertility level."""
    if level == "low":
        return "Apply NPK amendment and increase organic matter."
    if level == "medium":
        return "Monitor nutrients; consider light organic matter top-up."
    return "Soil fertility adequate; maintain current practice."


def main():
    data_file = find_data_file()
    if data_file is None:
        print("Error: raw_data.csv or raw_data.txt not found under data/agri-data/")
        return

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "soil_fertility_index_monitor_result.json"

    rows = []
    dropped = 0
    counts = {"low": 0, "medium": 0, "high": 0, "unknown": 0}
    low_flags = []

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, raw_row in enumerate(reader, start=1):
            row = {k.lower(): v for k, v in raw_row.items()}
            sfi = safe_float(row.get("sfi"), "sfi")
            if sfi is None:
                dropped += 1
                continue

            level = classify_sfi(sfi)
            counts[level] += 1
            entry = {
                "row_index": i,
                "sfi": round(sfi, 4),
                "level": level,
                "needs_amendment": level == "low",
                "recommendation": recommendation(level)
            }
            rows.append(entry)
            if level == "low":
                low_flags.append(entry)

    result = {
        "task_name": "Soil Fertility Index Monitor",
        "description": "Evaluates Soil Fertility Index (SFI) against low/medium/high thresholds and flags fields requiring soil amendment or organic matter adjustment.",
        "result_summary": [
            {"metric": "total_rows_processed", "value": len(rows)},
            {"metric": "rows_with_missing_sfi", "value": dropped},
            {"metric": "thresholds", "value": {"low": "< 0.65", "medium": "0.65 - 0.75", "high": ">= 0.75"}},
            {"metric": "category_counts", "value": counts},
            {"metric": "flagged_low_sfi_count", "value": len(low_flags)},
            {"metric": "flagged_low_sfi_rows", "value": low_flags[:20]}
        ],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Soil Fertility Index Monitor complete. Results saved to {out_file}")
    print(f"Category counts: {counts}")


if __name__ == "__main__":
    main()