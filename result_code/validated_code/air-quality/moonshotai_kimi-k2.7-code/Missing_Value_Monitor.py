"""
Task: Missing_Value_Monitor
Description: Scan the most recent hour of sensor readings for the missing-value tag -200 and report the count of missing values per column.
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

DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.csv")
if not os.path.exists(DATA_FILE_PATH):
    DATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "raw_data.txt")

METADATA_FILE_PATH = os.path.join(_root_dir, "data", "air-quality", "metadata.json")
OUTPUT_DIR = os.path.join(_root_dir, "output", "air-quality")
os.makedirs(OUTPUT_DIR, exist_ok=True)

import os
import sys
import csv
import json
from pathlib import Path
from datetime import datetime, timedelta


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    for name in ["raw_data.csv", "raw_data.txt"]:
        candidate = root_dir / "data" / "air-quality" / name
        if candidate.exists():
            return candidate
    return None


def parse_datetime(date_str, time_str):
    try:
        return datetime.strptime(f"{date_str} {time_str}", "%d-%m-%Y %H:%M:%S")
    except Exception:
        return None


def main():
    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/air-quality/", file=sys.stderr)
        sys.exit(1)

    numeric_cols = [
        "co(gt)", "pt08.s1(co)", "nmhc(gt)", "c6h6(gt)", "pt08.s2(nmhc)",
        "nox(gt)", "pt08.s3(nox)", "no2(gt)", "pt08.s4(no2)", "pt08.s5(o3)",
        "t", "rh", "ah"
    ]

    rows = []
    dropped = 0
    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower(): v for k, v in row.items()}
            dt = parse_datetime(row.get("date", ""), row.get("time", ""))
            if dt is None:
                dropped += 1
                continue
            row["_dt"] = dt
            rows.append(row)

    if not rows:
        print("Error: No valid rows found in data file.", file=sys.stderr)
        sys.exit(1)

    latest_dt = max(r["_dt"] for r in rows)
    hour_start = latest_dt.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)

    recent_rows = [r for r in rows if hour_start <= r["_dt"] < hour_end]

    counts = {col: 0 for col in numeric_cols}
    for r in recent_rows:
        for col in numeric_cols:
            val = r.get(col, "").strip().lower()
            if val == "-200":
                counts[col] += 1

    summary = []
    for col, cnt in counts.items():
        if cnt > 0:
            summary.append({"column": col, "missing_count": cnt})

    if not summary:
        summary.append({"message": "No -200 missing-value tags in the most recent hour."})

    summary.append({"latest_hour": latest_dt.strftime("%d-%m-%Y %H:%M:%S")})
    summary.append({"rows_scanned_in_hour": len(recent_rows)})
    summary.append({"dropped_rows_total": dropped})

    result = {
        "task_name": "Missing_Value_Monitor",
        "description": "Scan the most recent hour of sensor readings for the missing-value tag -200 and report the count of missing values per column.",
        "result_summary": summary,
        "result_generated_at": datetime.utcnow().isoformat() + "Z"
    }

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "Missing_Value_Monitor_result.json"

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Saved result to {out_file}")


if __name__ == "__main__":
    main()