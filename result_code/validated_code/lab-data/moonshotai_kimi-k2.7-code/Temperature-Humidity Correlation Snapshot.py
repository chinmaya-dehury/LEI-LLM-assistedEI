"""
Task: Temperature-Humidity Correlation Snapshot
Description: Compute a lightweight Pearson-like correlation between recent temperature and humidity readings for each mote to detect sensor drift or environmental coupling changes.
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

import os
import sys
import csv
import math
import json
from pathlib import Path
from datetime import datetime, timezone


def find_data_file():
    """Locate raw_data.csv or raw_data.txt under the project-root data/lab-data folder."""
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


def is_missing(value):
    if value is None:
        return True
    s = str(value).strip()
    return s == "" or s.upper() in ("NA", "N/A", "NULL", "NONE")


def to_float(value, column_name):
    if is_missing(value):
        return None
    try:
        return float(value)
    except Exception:
        print(
            f"Warning: invalid numeric value in column '{column_name}': '{value}'",
            file=sys.stderr,
        )
        return None


def pearson_correlation(xs, ys):
    n = len(xs)
    if n < 2:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return None
    return numerator / (denom_x * denom_y)


def interpret(correlation):
    if correlation is None:
        return "insufficient data"
    if correlation < -0.7:
        return "strong negative coupling"
    if correlation < -0.3:
        return "moderate negative coupling"
    if correlation < 0.3:
        return "weak coupling"
    if correlation < 0.7:
        return "moderate positive coupling"
    return "strong positive coupling"


def main():
    data_file = find_data_file()
    if not data_file:
        print("Error: raw_data.csv/txt not found under data/lab-data/", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(
        "/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_google_gemini-3.1-flash-lite_run1"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "temperature_humidity_correlation_snapshot_result.json"

    required_columns = ["moteid", "temperature", "humidity", "epoch"]
    rows_by_mote = {}
    total_rows = 0
    dropped_rows = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Error: input file is empty", file=sys.stderr)
            sys.exit(1)

        fieldnames = [c.lower() for c in reader.fieldnames]
        missing = [c for c in required_columns if c not in fieldnames]
        if missing:
            print(f"Error: missing required columns: {missing}", file=sys.stderr)
            sys.exit(1)

        for raw_row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in raw_row.items()}

            mote_raw = row.get("moteid")
            if is_missing(mote_raw):
                dropped_rows += 1
                continue
            try:
                mote_id = int(float(mote_raw))
            except Exception:
                dropped_rows += 1
                continue

            temperature = to_float(row.get("temperature"), "temperature")
            humidity = to_float(row.get("humidity"), "humidity")
            epoch = to_float(row.get("epoch"), "epoch")

            if temperature is None or humidity is None or epoch is None:
                dropped_rows += 1
                continue

            rows_by_mote.setdefault(mote_id, []).append((epoch, temperature, humidity))

    result_summary = []
    for mote_id in sorted(rows_by_mote):
        entries = rows_by_mote[mote_id]
        entries.sort(key=lambda x: x[0])
        recent = entries[-100:]  # use the most recent 100 valid readings per mote
        temperatures = [e[1] for e in recent]
        humidities = [e[2] for e in recent]
        correlation = pearson_correlation(temperatures, humidities)

        result_summary.append(
            {
                "mote_id": mote_id,
                "readings_used": len(recent),
                "total_readings": len(entries),
                "correlation": round(correlation, 4) if correlation is not None else None,
                "interpretation": interpret(correlation),
            }
        )

    output = {
        "task_name": "Temperature-Humidity Correlation Snapshot",
        "description": "Lightweight Pearson-like correlation between recent temperature and humidity readings per mote to detect sensor drift or environmental coupling changes.",
        "result_summary": result_summary,
        "result_generated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(
        f"Processed {total_rows} rows, dropped {dropped_rows}. "
        f"Results saved to {out_file}"
    )


if __name__ == "__main__":
    main()