"""
Task: Soil Moisture Deficit Alert
Description: Detect when Soil_Moisture falls below a threshold suitable for the current soil type and growth stage, indicating a potential irrigation need.
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

import os
import sys
import csv
import json
import math
from pathlib import Path
from datetime import datetime, timezone

TASK_NAME = "Soil Moisture Deficit Alert"
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_moonshotai_kimi-k2.7-code_nvidia_nemotron-3-ultra-550b-a55b_run1")

def find_data_file():
    curr = Path(__file__).resolve().parent
    root = curr
    while root.name and not (root / "data").exists():
        parent = root.parent
        if parent == root:
            break
        root = parent
    for name in ["raw_data.csv", "raw_data.txt"]:
        p = root / "data" / "agri-data" / name
        if p.exists():
            return p
    return None

MISSING = {"", "NA", "N/A", "None", "None"}

def is_missing(v):
    if v is None:
        return True
    return str(v).strip() in MISSING

def to_float(v, col):
    if is_missing(v):
        return None
    try:
        return float(v)
    except Exception:
        print(f"Warning: invalid numeric value in column '{col}': {v!r}", file=sys.stderr)
        return None

def to_int(v, col):
    if is_missing(v):
        return None
    try:
        return int(float(v))
    except Exception:
        print(f"Warning: invalid integer value in column '{col}': {v!r}", file=sys.stderr)
        return None

THRESHOLDS = {
    1: {1: 35.0, 2: 30.0, 3: 25.0},
    2: {1: 30.0, 2: 25.0, 3: 22.0},
    3: {1: 25.0, 2: 20.0, 3: 18.0},
}

SOIL_NAMES = {1: "Sandy", 2: "Loamy", 3: "Clay"}
GROWTH_NAMES = {1: "Seedling", 2: "Vegetative", 3: "Flowering"}

def threshold_for(soil_type, growth_stage):
    return THRESHOLDS.get(soil_type, {}).get(growth_stage, 30.0)

def main():
    import argparse
    parser = argparse.ArgumentParser(description=TASK_NAME)
    parser.add_argument("--strict", action="store_true", help="Skip rows with missing required fields")
    args = parser.parse_args()

    data_file = find_data_file()
    if not data_file or not data_file.exists():
        print("Error: raw_data.csv/txt not found under data/agri-data/", file=sys.stderr)
        sys.exit(1)

    alerts = []
    total_rows = 0
    valid_rows = 0
    dropped = 0

    with data_file.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            soil_moisture = to_float(row.get("soil_moisture"), "soil_moisture")
            soil_type = to_int(row.get("soil_type"), "soil_type")
            growth_stage = to_int(row.get("growth_stage"), "growth_stage")
            label = row.get("label", "unknown")

            if None in (soil_moisture, soil_type, growth_stage):
                dropped += 1
                print(f"Row {idx}: missing/invalid required fields (soil_moisture={row.get('soil_moisture')}, soil_type={row.get('soil_type')}, growth_stage={row.get('growth_stage')})", file=sys.stderr)
                continue

            valid_rows += 1
            threshold = threshold_for(soil_type, growth_stage)
            if soil_moisture < threshold:
                deficit = threshold - soil_moisture
                severity = "high" if deficit >= 10 else ("moderate" if deficit >= 5 else "low")
                alerts.append({
                    "row": idx,
                    "crop": label,
                    "soil_type": SOIL_NAMES.get(soil_type, str(soil_type)),
                    "growth_stage": GROWTH_NAMES.get(growth_stage, str(growth_stage)),
                    "soil_moisture": round(soil_moisture, 2),
                    "threshold": threshold,
                    "deficit": round(deficit, 2),
                    "severity": severity,
                })

    alert_count = len(alerts)
    alert_rate = (alert_count / valid_rows * 100) if valid_rows else 0.0
    avg_deficit = sum(a["deficit"] for a in alerts) / alert_count if alert_count else 0.0

    by_soil = {}
    by_stage = {}
    for a in alerts:
        by_soil.setdefault(a["soil_type"], 0)
        by_soil[a["soil_type"]] += 1
        by_stage.setdefault(a["growth_stage"], 0)
        by_stage[a["growth_stage"]] += 1

    summary = {
        "total_rows": total_rows,
        "valid_rows": valid_rows,
        "dropped_rows": dropped,
        "alert_count": alert_count,
        "alert_rate_percent": round(alert_rate, 2),
        "average_deficit": round(avg_deficit, 2),
        "alerts_by_soil_type": by_soil,
        "alerts_by_growth_stage": by_stage,
        "sample_alerts": alerts[:10],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{TASK_NAME}_result.json"
    result = {
        "task_name": TASK_NAME,
        "description": "Detect when Soil_Moisture falls below a threshold suitable for the current soil type and growth stage, indicating a potential irrigation need.",
        "result_summary": [summary],
        "result_generated_at": datetime.now(timezone.utc).isoformat(),
    }
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved results to {out_path}")
    print(f"Alerts: {alert_count}/{valid_rows} ({alert_rate:.2f}%)")

if __name__ == "__main__":
    main()