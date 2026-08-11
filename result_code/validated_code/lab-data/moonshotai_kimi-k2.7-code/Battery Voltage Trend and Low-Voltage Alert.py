"""
Task: Battery Voltage Trend and Low-Voltage Alert
Description: Track each mote's voltage over recent epochs, detect downward trends or values below a safe threshold, and raise alerts for potential battery depletion or power issues.
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
import json
import math
import argparse
from datetime import datetime, timezone
from pathlib import Path

MISSING_MARKERS = {"", "NA", "N/A", "None", "None", "nan"}

def is_missing(value):
    if value is None:
        return True
    return str(value).strip() in MISSING_MARKERS

def safe_float(value, col_name, log):
    if is_missing(value):
        return None
    try:
        return float(value)
    except Exception as e:
        log.append(f"Invalid numeric value in column '{col_name}': '{value}'")
        return None

def safe_int(value, col_name, log):
    if is_missing(value):
        return None
    try:
        return int(float(value))
    except Exception as e:
        log.append(f"Invalid integer value in column '{col_name}': '{value}'")
        return None

def find_project_root():
    curr_dir = Path(__file__).resolve().parent
    root_dir = curr_dir
    while root_dir.name and not (root_dir / "data").exists():
        parent = root_dir.parent
        if parent == root_dir:
            break
        root_dir = parent
    return root_dir

def resolve_input_file(root_dir):
    candidates = [
        root_dir / "data" / "lab-data" / "raw_data.csv",
        root_dir / "data" / "lab-data" / "raw_data.txt",
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return None

def linear_slope(values):
    n = len(values)
    if n < 2:
        return 0.0
    sum_x = sum(v[0] for v in values)
    sum_y = sum(v[1] for v in values)
    sum_xy = sum(v[0] * v[1] for v in values)
    sum_x2 = sum(v[0] * v[0] for v in values)
    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom

def main():
    parser = argparse.ArgumentParser(description="Battery voltage trend and low-voltage alert")
    parser.add_argument("--strict", action="store_true", help="Skip rows with missing required fields")
    parser.add_argument("--window", type=int, default=20, help="Number of recent readings for trend")
    parser.add_argument("--threshold", type=float, default=2.4, help="Low voltage alert threshold (V)")
    parser.add_argument("--trend-threshold", type=float, default=-0.001, help="Downward trend alert threshold (V/epoch)")
    args = parser.parse_args()

    root_dir = find_project_root()
    data_file = resolve_input_file(root_dir)
    if data_file is None:
        print("Error: Could not find data/lab-data/raw_data.csv or raw_data.txt", file=sys.stderr)
        sys.exit(1)

    log = []
    required = {"moteid", "voltage", "epoch"}
    mote_data = {}
    total_rows = 0
    dropped_rows = 0

    with open(data_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            row = {k.lower(): v for k, v in row.items()}
            missing_cols = [c for c in required if c not in row or is_missing(row.get(c))]
            if missing_cols:
                msg = f"Row {total_rows}: missing/invalid required columns {missing_cols}"
                if args.strict:
                    log.append(msg + " (skipped due to --strict)")
                else:
                    log.append(msg + " (skipped)")
                dropped_rows += 1
                continue
            mote_id = safe_int(row.get("moteid"), "moteid", log)
            epoch = safe_int(row.get("epoch"), "epoch", log)
            voltage = safe_float(row.get("voltage"), "voltage", log)
            if mote_id is None or epoch is None or voltage is None:
                dropped_rows += 1
                continue
            mote_data.setdefault(mote_id, []).append((epoch, voltage))

    if not mote_data:
        print("Error: No valid voltage readings found.", file=sys.stderr)
        sys.exit(1)

    if log:
        print(f"Parse warnings ({len(log)} total, showing first 10):", file=sys.stderr)
        for msg in log[:10]:
            print(msg, file=sys.stderr)

    summary = []
    alerts = 0
    for mote_id in sorted(mote_data):
        readings = sorted(mote_data[mote_id], key=lambda x: x[0])
        voltages = [v for _, v in readings]
        mean_v = sum(voltages) / len(voltages)
        min_v = min(voltages)
        max_v = max(voltages)
        recent = readings[-args.window:]
        slope = linear_slope(recent)
        reasons = []
        if min_v < args.threshold:
            reasons.append(f"low voltage {min_v:.3f}V below threshold {args.threshold}V")
        if slope < args.trend_threshold:
            reasons.append(f"downward trend slope {slope:.6f} V/epoch")
        alert = len(reasons) > 0
        if alert:
            alerts += 1
        summary.append({
            "moteid": mote_id,
            "readings_count": len(voltages),
            "mean_voltage_V": round(mean_v, 4),
            "min_voltage_V": round(min_v, 4),
            "max_voltage_V": round(max_v, 4),
            "recent_window": len(recent),
            "trend_slope_V_per_epoch": round(slope, 6),
            "alert": alert,
            "alert_reasons": reasons
        })

    overall = {
        "summary_type": "overall",
        "input_file": str(data_file),
        "total_rows_read": total_rows,
        "dropped_rows": dropped_rows,
        "motes_analyzed": len(summary),
        "alerts_count": alerts,
        "low_voltage_threshold_V": args.threshold,
        "trend_threshold_V_per_epoch": args.trend_threshold
    }

    result = {
        "task_name": "Battery Voltage Trend and Low-Voltage Alert",
        "description": "Track each mote's voltage over recent epochs, detect downward trends or values below a safe threshold, and raise alerts for potential battery depletion or power issues.",
        "result_summary": [overall] + summary,
        "result_generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }

    out_dir = Path("/home/dcc/LEI-Models-Comparision/output/lab-data/lab-data_moonshotai_kimi-k2.7-code_anthropic_claude-3-haiku_run2")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "battery_voltage_trend_and_low_voltage_alert_result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Analyzed {len(summary)} motes, {alerts} alerts. Output saved to {out_file}")

if __name__ == "__main__":
    main()