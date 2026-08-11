import re
"""
Task: Photosynthesis Potential Monitoring
Description: Flag low Photosynthesis Potential (PP) values that suggest reduced photosynthetic activity based on sunlight exposure, CO2 concentration, and temperature.
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

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

TASK_NAME = "Photosynthesis Potential Monitoring"
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1")

def find_data_file():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    for name in ("raw_data.csv", "raw_data.txt"):
        candidate = root_dir / "data" / "agri-data" / name
        if candidate.exists():
            return candidate
    return None

def to_float(value, col):
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.upper() in {"NA", "N/A", "NULL"}:
        return None
    try:
        return float(s)
    except ValueError:
        print(f"Warning: invalid numeric value in column '{col}': {value!r}", file=sys.stderr)
        return None

def percentile(values, p):
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    k = (n - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] * (c - k) + s[c] * (k - f)

def main():
    parser = argparse.ArgumentParser(description="Photosynthesis Potential Monitoring")
    parser.add_argument("--strict", action="store_true", help="Drop rows missing any PP driver even if PP is present")
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file or not data_file.exists():
        print("Error: raw_data.csv or raw_data.txt not found under data/agri-data/", file=sys.stderr)
        sys.exit(1)

    rows = []
    dropped = 0
    with data_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Error: input file has no headers", file=sys.stderr)
            sys.exit(1)
        for i, row in enumerate(reader, start=1):
            row = {k.lower().strip(): v for k, v in row.items()}
            pp = to_float(row.get("pp"), "pp")
            sunlight = to_float(row.get("sunlight_exposure"), "sunlight_exposure")
            co2 = to_float(row.get("co2_concentration"), "co2_concentration")
            temp = to_float(row.get("temperature"), "temperature")

            if pp is None:
                if sunlight is None or co2 is None or temp is None:
                    dropped += 1
                    continue
                pp = (sunlight / 24.0) * (co2 / 1000.0) * (temp / 50.0)
            else:
                if args.strict:
                    if sunlight is None or co2 is None or temp is None:
                        dropped += 1
                        continue

            rows.append({
                "row": i,
                "pp": pp,
                "sunlight_exposure": sunlight,
                "co2_concentration": co2,
                "temperature": temp,
                "label": row.get("label", "")
            })

    if not rows:
        print("Error: no valid rows found", file=sys.stderr)
        sys.exit(1)

    pp_values = [r["pp"] for r in rows if r["pp"] is not None]
    threshold = percentile(pp_values, 0.25)
    flagged = []
    for r in rows:
        if r["pp"] is not None and r["pp"] < threshold:
            flagged.append({
                "row": r["row"],
                "pp": round(r["pp"], 4),
                "sunlight_exposure": r["sunlight_exposure"],
                "co2_concentration": r["co2_concentration"],
                "temperature": r["temperature"],
                "label": r["label"],
                "reason": f"PP below lower-quartile threshold ({threshold:.4f})"
            })

    result = {
        "task_name": TASK_NAME,
        "description": "Flag low Photosynthesis Potential (PP) values that suggest reduced photosynthetic activity based on sunlight exposure, CO2 concentration, and temperature.",
        "result_summary": [
            {
                "type": "summary",
                "total_rows": len(rows) + dropped,
                "valid_rows": len(rows),
                "dropped_rows": dropped,
                "threshold": round(threshold, 4) if threshold is not None else None,
                "flagged_count": len(flagged)
            }
        ] + flagged,
        "result_generated_at": datetime.now(timezone.utc).isoformat()
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"{TASK_NAME}_result.json"
    with out_file.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved {TASK_NAME} results to {out_file}")
    print(f"Flagged {len(flagged)} of {len(rows)} rows with PP below {threshold:.4f}")

if __name__ == "__main__":
    main()