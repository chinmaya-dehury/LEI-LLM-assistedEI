"""
Task: Diurnal Light Pattern Detection
Description: Classify each mote's light readings into day/occupied versus night/unoccupied states using a low-complexity threshold, and report daily pattern consistency for occupancy-aware energy control.
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
from datetime import datetime
from pathlib import Path

TASK_NAME = "Diurnal Light Pattern Detection"
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2")
OUTPUT_FILE = OUTPUT_DIR / f"{TASK_NAME.replace(' ', '_')}_result.json"

MISSING = {"", "NA", "N/A", "None", "NULL", "None"}


def find_data_file():
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


def to_float(value, col_name):
    if value is None:
        return None
    s = str(value).strip()
    if s in MISSING:
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value in '{col_name}': {value!r}; treating as missing.", file=sys.stderr)
        return None


def parse_date(date_str, time_str):
    s = f"{date_str.strip()} {time_str.strip()}"
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def main():
    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv or raw_data.txt not found under data/lab-data/.", file=sys.stderr)
        sys.exit(1)

    threshold = float(os.environ.get("LIGHT_THRESHOLD", "100.0"))

    rows_read = 0
    rows_dropped = 0
    per_mote = {}
    per_mote_date = {}

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw_row in reader:
            rows_read += 1
            row = {k.lower(): v for k, v in raw_row.items()}
            mote = row.get("moteid")
            date = row.get("date")
            time = row.get("time")
            light = to_float(row.get("light"), "light")

            if mote is None or str(mote).strip() in MISSING or date is None or str(date).strip() in MISSING or light is None:
                rows_dropped += 1
                continue

            mote = str(mote).strip()
            date_key = str(date).strip()
            time_val = time if time and str(time).strip() not in MISSING else "00:00:00"
            dt = parse_date(date_key, time_val)
            if dt is None:
                rows_dropped += 1
                continue

            state = "day" if light >= threshold else "night"

            if mote not in per_mote:
                per_mote[mote] = {"day": 0, "night": 0}
            per_mote[mote][state] += 1

            mdate = (mote, date_key)
            if mdate not in per_mote_date:
                per_mote_date[mdate] = {"day": 0, "night": 0}
            per_mote_date[mdate][state] += 1

    if rows_read == 0:
        print("Error: no rows read from input file.", file=sys.stderr)
        sys.exit(1)

    summary = []
    summary.append({
        "metric": "processing_summary",
        "rows_read": rows_read,
        "rows_dropped": rows_dropped,
        "light_threshold_lux": threshold
    })

    for mote in sorted(per_mote.keys(), key=lambda x: int(x) if x.isdigit() else x):
        counts = per_mote[mote]
        total = counts["day"] + counts["night"]
        day_ratio = counts["day"] / total if total > 0 else 0.0
        summary.append({
            "metric": "mote_pattern",
            "moteid": mote,
            "total_readings": total,
            "day_occupied_count": counts["day"],
            "night_unoccupied_count": counts["night"],
            "day_occupied_ratio": round(day_ratio, 4),
            "dominant_state": "day_occupied" if day_ratio >= 0.5 else "night_unoccupied"
        })

    mote_dates = {}
    for (mote, date_key), counts in per_mote_date.items():
        mote_dates.setdefault(mote, {"dates_with_day": 0, "dates_total": 0})
        mote_dates[mote]["dates_total"] += 1
        if counts["day"] > 0:
            mote_dates[mote]["dates_with_day"] += 1

    for mote in sorted(mote_dates.keys(), key=lambda x: int(x) if x.isdigit() else x):
        info = mote_dates[mote]
        consistency = info["dates_with_day"] / info["dates_total"] if info["dates_total"] > 0 else 0.0
        summary.append({
            "metric": "daily_consistency",
            "moteid": mote,
            "dates_total": info["dates_total"],
            "dates_with_day_occupied": info["dates_with_day"],
            "day_consistency_ratio": round(consistency, 4)
        })

    result = {
        "task_name": TASK_NAME,
        "description": "Classify each mote's light readings into day/occupied versus night/unoccupied states using a low-complexity threshold, and report daily pattern consistency for occupancy-aware energy control.",
        "result_summary": summary,
        "result_generated_at": datetime.utcnow().isoformat() + "Z"
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved results to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()