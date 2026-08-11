"""
Task: Temperature Trend Change Detection
Description: For each mote, compute the difference between the latest temperature and a short rolling average to detect rising or falling temperature trends in real time.
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

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

TASK_NAME = "temperature_trend_change_detection"
WINDOW_SIZE = 5
TEMP_MIN = 0.0
TEMP_MAX = 50.0
STABLE_THRESHOLD = 0.1

MISSING = {"", "na", "n/a", "None", "none"}


def is_missing(value):
    if value is None:
        return True
    return value.strip().lower() in MISSING


def to_float(value, col):
    if is_missing(value):
        return None
    try:
        return float(value)
    except ValueError:
        print(
            f"Invalid numeric value in column '{col}': '{value}'",
            file=sys.stderr,
        )
        return None


def resolve_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    data_file = root_dir / "data" / "lab-data" / "raw_data.csv"
    if not data_file.exists():
        data_file = root_dir / "data" / "lab-data" / "raw_data.txt"
    return data_file


def main():
    parser = argparse.ArgumentParser(
        description="Detect per-mote temperature trend changes."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Abort if any rows are dropped or invalid.",
    )
    args = parser.parse_args()

    data_file = resolve_data_file()
    if not data_file.exists():
        print(
            f"Input file not found: expected {data_file.parent}/raw_data.csv or .txt",
            file=sys.stderr,
        )
        sys.exit(1)

    required = {"moteid", "temperature", "epoch"}
    mote_readings = defaultdict(list)
    dropped = 0
    invalid_temp = 0
    row_count = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            print("Empty input file.", file=sys.stderr)
            sys.exit(1)

        header = {h.lower().strip(): h for h in reader.fieldnames}
        missing_cols = required - set(header.keys())
        if missing_cols:
            print(f"Missing required columns: {missing_cols}", file=sys.stderr)
            sys.exit(1)

        mote_col = header["moteid"]
        temp_col = header["temperature"]
        epoch_col = header["epoch"]

        for row in reader:
            row_count += 1
            mote_raw = row.get(mote_col)
            temp_raw = row.get(temp_col)
            epoch_raw = row.get(epoch_col)

            if is_missing(mote_raw) or is_missing(temp_raw) or is_missing(epoch_raw):
                dropped += 1
                continue

            try:
                mote_id = int(float(mote_raw))
            except ValueError:
                print(
                    f"Invalid moteid value: '{mote_raw}'",
                    file=sys.stderr,
                )
                dropped += 1
                continue

            try:
                epoch = int(float(epoch_raw))
            except ValueError:
                print(
                    f"Invalid epoch value: '{epoch_raw}'",
                    file=sys.stderr,
                )
                dropped += 1
                continue

            temp = to_float(temp_raw, "temperature")
            if temp is None:
                invalid_temp += 1
                dropped += 1
                continue

            if not (TEMP_MIN <= temp <= TEMP_MAX):
                print(
                    f"Temperature out of range for mote {mote_id}: {temp}",
                    file=sys.stderr,
                )
                invalid_temp += 1
                dropped += 1
                continue

            mote_readings[mote_id].append((epoch, temp))

    if row_count == 0:
        print("No rows read.", file=sys.stderr)
        sys.exit(1)

    if args.strict and dropped > 0:
        print(
            f"Strict mode: {dropped} rows dropped or invalid. Aborting.",
            file=sys.stderr,
        )
        sys.exit(1)

    results = []
    for mote_id, readings in mote_readings.items():
        readings.sort(key=lambda x: x[0])
        latest_epoch, latest_temp = readings[-1]

        if len(readings) < 2:
            results.append(
                {
                    "moteid": mote_id,
                    "latest_temperature": round(latest_temp, 4),
                    "rolling_average": None,
                    "temperature_change": None,
                    "trend": "insufficient_data",
                    "window_size": 0,
                    "latest_epoch": latest_epoch,
                }
            )
            continue

        prev_window = readings[-(WINDOW_SIZE + 1):-1]
        prev_temps = [t for _, t in prev_window]
        avg = sum(prev_temps) / len(prev_temps)
        change = latest_temp - avg

        if change > STABLE_THRESHOLD:
            trend = "rising"
        elif change < -STABLE_THRESHOLD:
            trend = "falling"
        else:
            trend = "stable"

        results.append(
            {
                "moteid": mote_id,
                "latest_temperature": round(latest_temp, 4),
                "rolling_average": round(avg, 4),
                "temperature_change": round(change, 4),
                "trend": trend,
                "window_size": len(prev_temps),
                "latest_epoch": latest_epoch,
            }
        )

    results.sort(key=lambda x: x["moteid"])

    output_dir = Path(
        "/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{TASK_NAME}_result.json"

    result_doc = {
        "task_name": TASK_NAME,
        "description": (
            "For each mote, compare the latest temperature against the average of "
            "the previous up-to-5 readings to detect rising, falling, or stable trends."
        ),
        "result_summary": results,
        "result_generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result_doc, f, indent=2)

    print(f"Saved results to {output_file}")
    print(
        f"Rows read: {row_count}, dropped/invalid: {dropped}, "
        f"invalid temperature values: {invalid_temp}, motes: {len(mote_readings)}"
    )


if __name__ == "__main__":
    main()