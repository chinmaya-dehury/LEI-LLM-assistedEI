"""
Task: Missing Sensor Reading Flag
Description: Identify and count occurrences of the -200 missing-value tag in each sensor and reference column per hour, producing a lightweight health indicator for data completeness.
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
from datetime import datetime, timezone

REQUIRED_COLUMNS = [
    "date", "time", "co(gt)", "pt08.s1(co)", "nmhc(gt)", "c6h6(gt)",
    "pt08.s2(nmhc)", "nox(gt)", "pt08.s3(nox)", "no2(gt)", "pt08.s4(no2)",
    "pt08.s5(o3)", "t", "rh", "ah"
]


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for fname in ("raw_data.csv", "raw_data.txt"):
        fpath = root_dir / "data" / "air-quality" / fname
        if fpath.exists():
            return fpath
    return None


def is_missing(value):
    if value is None:
        return True
    s = str(value).strip()
    if s == "":
        return True
    if s.upper() in ("NA", "N/A", "NULL"):
        return True
    try:
        if float(s) == -200.0:
            return True
    except ValueError:
        pass
    return False


def main():
    strict_mode = "--strict" in sys.argv
    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/air-quality/", file=sys.stderr)
        sys.exit(1)

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "Missing Sensor Reading Flag_result.json"

    col_missing = {}
    hourly_health = []
    total_rows = 0
    rows_with_missing = 0
    max_missing_in_row = 0
    dropped_rows = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Error: CSV has no header row.", file=sys.stderr)
            sys.exit(1)

        fieldnames = [fn.strip() for fn in reader.fieldnames if fn.strip()]
        for c in fieldnames:
            col_missing[c] = 0

        for row_num, row in enumerate(reader, start=2):
            try:
                row = {k.lower().strip(): v for k, v in row.items()}
                total_rows += 1
                row_missing = 0
                for c in fieldnames:
                    key = c.lower()
                    val = row.get(key, "")
                    if is_missing(val):
                        col_missing[c] += 1
                        row_missing += 1

                if row_missing:
                    rows_with_missing += 1
                if row_missing > max_missing_in_row:
                    max_missing_in_row = row_missing

                hourly_health.append({
                    "hour": f"{row.get('date', '')} {row.get('time', '')}".strip(),
                    "missing_count": row_missing
                })
            except Exception as e:
                dropped_rows += 1
                print(f"Warning: row {row_num} skipped due to error: {e}", file=sys.stderr)

    if strict_mode and rows_with_missing > 0:
        print(f"Strict mode enabled: {rows_with_missing} rows contain missing values. Exiting.", file=sys.stderr)
        sys.exit(1)

    result = {
        "task_name": "Missing Sensor Reading Flag",
        "description": "Identify and count occurrences of the -200 missing-value tag in each sensor and reference column per hour, producing a lightweight health indicator for data completeness.",
        "result_summary": [
            {"total_rows_read": total_rows},
            {"rows_with_any_missing": rows_with_missing},
            {"max_missing_columns_in_one_hour": max_missing_in_row},
            {"dropped_rows": dropped_rows},
            {"missing_count_by_column": col_missing},
            {"hourly_missing_counts": hourly_health}
        ],
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Result saved to {out_file}")


if __name__ == "__main__":
    main()