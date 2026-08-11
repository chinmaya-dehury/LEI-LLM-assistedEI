"""
Task: Daily Temperature Extremes per Mote
Description: Maintain daily minimum and maximum temperature values for each mote to support trend summaries and threshold compliance checks.
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
import math
from pathlib import Path
from datetime import datetime

TASK_NAME = "daily_temperature_extremes_per_mote"
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1")

def resolve_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ("raw_data.csv", "raw_data.txt"):
        candidate = root_dir / "data" / "lab-data" / name
        if candidate.exists():
            return candidate
    return None

def safe_float(value, column):
    if value is None:
        return None
    v = value.strip()
    if v == "" or v.upper() in ("NA", "N/A", "NULL"):
        return None
    try:
        return float(v)
    except ValueError:
        print(f"Warning: invalid numeric value in column '{column}': {value!r}")
        return None

def main():
    data_file = resolve_data_file()
    if data_file is None:
        print("Error: raw_data.csv or raw_data.txt not found under data/lab-data/")
        return
    print(f"Reading data from: {data_file}")

    extremes = {}
    total_rows = 0
    dropped_rows = 0

    required = {"date", "moteid", "temperature"}

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            if not required.issubset(row):
                dropped_rows += 1
                print(f"Warning: missing required columns in row {total_rows}")
                continue
            date = row.get("date", "").strip()
            mote = row.get("moteid", "").strip()
            temp = safe_float(row.get("temperature"), "temperature")
            if not date or not mote or temp is None:
                dropped_rows += 1
                continue
            key = (date, mote)
            if key not in extremes:
                extremes[key] = {"min": temp, "max": temp}
            else:
                if temp < extremes[key]["min"]:
                    extremes[key]["min"] = temp
                if temp > extremes[key]["max"]:
                    extremes[key]["max"] = temp

    summary = []
    for (date, mote), vals in sorted(extremes.items()):
        summary.append({
            "date": date,
            "moteid": mote,
            "min_temperature": vals["min"],
            "max_temperature": vals["max"]
        })

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = {
        "task_name": TASK_NAME,
        "description": "Daily minimum and maximum temperature per mote.",
        "result_summary": summary,
        "result_generated_at": datetime.utcnow().isoformat() + "Z"
    }
    out_path = OUTPUT_DIR / f"{TASK_NAME}_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Total rows processed: {total_rows}")
    print(f"Dropped/invalid rows: {dropped_rows}")
    print(f"Daily extremes records: {len(summary)}")
    print(f"Result saved to: {out_path}")

if __name__ == "__main__":
    main()