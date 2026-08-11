import json
import sys
import math
import csv
"""
Task: Temperature_Humidity_Sensor_Cross_Sensitivity_Indicator
Description: Compute the Pearson correlation between temperature/relative-humidity and each PT08 sensor resistance over a sliding 7-day window to identify potential cross-sensitivity patterns.
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

import argparse, csv, json, math, sys
from datetime import datetime, timedelta
from pathlib import Path

TASK_NAME = "Temperature_Humidity_Sensor_Cross_Sensitivity_Indicator"
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/air-quality/air-quality_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2")
OUTPUT_FILE = OUTPUT_DIR / f"{TASK_NAME}_result.json"

MISSING = {"", "NA", "N/A", "None", "NULL", "None"}
SENSOR_COLS = [
    "pt08.s1(co)",
    "pt08.s2(nmhc)",
    "pt08.s3(nox)",
    "pt08.s4(no2)",
    "pt08.s5(o3)",
]
ENV_COLS = ["t", "rh"]


def find_data_file(root):
    for ext in ["csv", "txt"]:
        f = root / "data" / "air-quality" / f"raw_data.{ext}"
        if f.exists():
            return f
    return None


def parse_num(value):
    if value is None:
        return None
    s = str(value).strip()
    if s in MISSING:
        return None
    try:
        f = float(s)
        if f <= -200:
            return None
        return f
    except ValueError:
        return None


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    if dx <= 0 or dy <= 0:
        return None
    return num / math.sqrt(dx * dy)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="Drop rows with any missing env/sensor values")
    args = parser.parse_args()

    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent

    data_file = find_data_file(root_dir)
    if not data_file:
        print("Data file not found under data/air-quality/", file=sys.stderr)
        sys.exit(1)

    records = []
    dropped = 0
    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.lower().strip(): v for k, v in row.items()}
            date_str = row.get("date")
            time_str = row.get("time")
            if not date_str or not time_str:
                dropped += 1
                continue
            try:
                dt = datetime.strptime(f"{date_str.strip()} {time_str.strip()}", "%d-%m-%Y %H:%M:%S")
            except ValueError:
                dropped += 1
                continue
            rec = {"dt": dt}
            missing_in_row = False
            for col in ENV_COLS + SENSOR_COLS:
                v = parse_num(row.get(col))
                rec[col] = v
                if v is None:
                    missing_in_row = True
            if args.strict and missing_in_row:
                dropped += 1
                continue
            records.append(rec)

    records.sort(key=lambda r: r["dt"])
    print(f"Loaded {len(records)} records, dropped {dropped} rows.")

    if len(records) < 24:
        print("Insufficient data for 7-day windows.", file=sys.stderr)
        sys.exit(1)

    window_results = []
    n = len(records)
    window_len = timedelta(days=7)
    step = timedelta(days=1)
    start_dt = records[0]["dt"]
    end_dt = records[-1]["dt"]
    current = start_dt
    i = 0

    while current <= end_dt:
        while i < n and records[i]["dt"] < current:
            i += 1
        j = i
        while j < n and records[j]["dt"] < current + window_len:
            j += 1
        window_records = records[i:j]
        if len(window_records) >= 24:
            entry = {
                "window_start": current.isoformat(),
                "window_end": (current + window_len).isoformat(),
                "records_count": len(window_records),
            }
            for env in ENV_COLS:
                for sensor in SENSOR_COLS:
                    xs = []
                    ys = []
                    for r in window_records:
                        ev = r[env]
                        sv = r[sensor]
                        if ev is not None and sv is not None:
                            xs.append(ev)
                            ys.append(sv)
                    corr = pearson(xs, ys)
                    key = f"{env}_vs_{sensor}"
                    entry[key] = round(corr, 4) if corr is not None else None
            window_results.append(entry)
        current += step

    agg = {}
    counts = {}
    for wr in window_results:
        for k, v in wr.items():
            if k in ("window_start", "window_end", "records_count"):
                continue
            if v is not None:
                agg[k] = agg.get(k, 0.0) + v
                counts[k] = counts.get(k, 0) + 1
    avg = {k: round(agg[k] / counts[k], 4) for k in agg}

    result = {
        "task_name": TASK_NAME,
        "description": "Compute the Pearson correlation between temperature/relative-humidity and each PT08 sensor resistance over a sliding 7-day window to identify potential cross-sensitivity patterns.",
        "result_summary": [
            {
                "aggregate_correlations": avg,
                "windows_count": len(window_results),
                "dropped_rows": dropped,
                "total_rows": len(records),
            }
        ] + window_results,
        "result_generated_at": datetime.now().isoformat(),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved results to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()