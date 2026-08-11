"""
Task: Benzene-NMHC Coherence Check
Description: Monitor the rolling correlation or ratio between Benzene and NMHC reference concentrations to detect changes in source composition or drift in hydrocarbon sensing.
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

import argparse
import csv
import json
import math
import sys
from datetime import datetime
from pathlib import Path

TASK_NAME = "Benzene-NMHC Coherence Check"
DESCRIPTION = "Monitor the rolling correlation or ratio between Benzene and NMHC reference concentrations to detect changes in source composition or drift in hydrocarbon sensing."
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run2")
WINDOW_SIZE = 24

MISSING_STRINGS = {"", "NA", "N/A", "None", "NULL", "None"}
MISSING_NUMERIC_SENTINELS = {-200.0}


def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ("raw_data.csv", "raw_data.txt"):
        candidate = root_dir / "data" / "air-quality" / name
        if candidate.exists():
            return candidate
    return None


def is_missing(value):
    if value is None:
        return True
    return str(value).strip() in MISSING_STRINGS


def to_float(value, col_name):
    if is_missing(value):
        return None
    s = str(value).strip()
    try:
        v = float(s)
        if v in MISSING_NUMERIC_SENTINELS:
            return None
        return v
    except ValueError:
        print(f"Warning: cannot parse {col_name} value {value!r}; treating as missing.", file=sys.stderr)
        return None


def pearson(x, y):
    n = len(x)
    if n < 2:
        return None
    mx = sum(x) / n
    my = sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    dy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def parse_datetime(row):
    d = row.get("date", "").strip()
    t = row.get("time", "").strip()
    if not d or not t:
        return None
    try:
        return datetime.strptime(f"{d} {t}", "%d-%m-%Y %H:%M:%S")
    except ValueError:
        return None


def main():
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--strict", action="store_true", help="Require both Benzene and NMHC on every row.")
    args = parser.parse_args()

    data_file = find_data_file()
    if data_file is None:
        print("Error: raw_data.csv or raw_data.txt not found under data/air-quality/.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading {data_file}")

    benzene = []
    nmhc = []
    timestamps = []
    dropped = 0
    total = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            row = {k.lower(): v for k, v in row.items()}
            b = to_float(row.get("c6h6(gt)"), "C6H6(GT)")
            n = to_float(row.get("nmhc(gt)"), "NMHC(GT)")
            if b is None or n is None:
                dropped += 1
                continue
            ts = parse_datetime(row)
            benzene.append(b)
            nmhc.append(n)
            timestamps.append(ts)

    print(f"Total rows: {total}, usable rows: {len(benzene)}, dropped/missing: {dropped}")

    if args.strict and dropped > 0:
        print(f"Strict mode: {dropped} rows with missing Benzene/NMHC were skipped.", file=sys.stderr)

    if len(benzene) < WINDOW_SIZE:
        print(f"Error: need at least {WINDOW_SIZE} complete rows.", file=sys.stderr)
        sys.exit(1)

    overall_corr = pearson(benzene, nmhc)
    overall_ratio = sum(b / n for b, n in zip(benzene, nmhc) if n != 0) / len(benzene)

    rolling = []
    for i in range(WINDOW_SIZE - 1, len(benzene)):
        window_b = benzene[i - WINDOW_SIZE + 1:i + 1]
        window_n = nmhc[i - WINDOW_SIZE + 1:i + 1]
        corr = pearson(window_b, window_n)
        n_sum = sum(window_n)
        ratio = sum(window_b) / n_sum if n_sum != 0 else None
        ts_str = timestamps[i].isoformat() if timestamps[i] else None
        rolling.append({
            "window_end": ts_str,
            "benzene_mean": round(sum(window_b) / WINDOW_SIZE, 4),
            "nmhc_mean": round(sum(window_n) / WINDOW_SIZE, 4),
            "benzene_nmhc_ratio": round(ratio, 4) if ratio is not None else None,
            "pearson_r": round(corr, 4) if corr is not None else None
        })

    result = {
        "task_name": TASK_NAME,
        "description": DESCRIPTION,
        "result_summary": [
            {
                "metric": "overall_pearson_correlation",
                "value": round(overall_corr, 4) if overall_corr is not None else None
            },
            {
                "metric": "overall_mean_benzene_nmhc_ratio",
                "value": round(overall_ratio, 4)
            },
            {
                "metric": "rolling_window_hours",
                "value": WINDOW_SIZE
            },
            {
                "metric": "rolling_windows",
                "value": len(rolling)
            },
            {
                "metric": "windows",
                "value": rolling
            }
        ],
        "result_generated_at": datetime.utcnow().isoformat() + "Z"
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{TASK_NAME}_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Result saved to {out_path}")


if __name__ == "__main__":
    main()