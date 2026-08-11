"""
Task: Soil Fertility Index Alert
Description: Monitor the Soil Fertility Index (SFI) and trigger an alert if it falls below a predefined threshold (e.g., 0.7), indicating potential nutrient deficiency requiring soil amendment.
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

import csv
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# --- Path Resolution ---
curr_dir = Path(__file__).resolve().parent
root_dir = curr_dir
while root_dir.name and not (root_dir / "data").exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / "data" / "agri-data" / "raw_data.csv"
if not data_file.exists():
    data_file = root_dir / "data" / "agri-data" / "raw_data.txt"

if not data_file.exists():
    print("ERROR: Input data file not found under data/agri-data/")
    sys.exit(1)

# --- Output Path ---
OUTPUT_DIR = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_google_gemini-3.1-flash-lite_run2")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
output_file = OUTPUT_DIR / "Soil Fertility Index Alert_result.json"

# --- Config ---
SFI_THRESHOLD = 0.7
MISSING_VALUES = {"", "NA", "N/A", "None", "None", "nan"}

def safe_float(value):
    if value is None:
        return None
    v = str(value).strip()
    if v.lower() in MISSING_VALUES:
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

# --- Read Data ---
rows = []
missing_count = 0
invalid_count = 0

try:
    with open(data_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            sfi_val = safe_float(row.get("sfi"))
            if sfi_val is None:
                missing_count += 1
                continue
            rows.append({
                "sfi": sfi_val,
                "label": row.get("label", "unknown"),
                "temperature": safe_float(row.get("temperature")),
                "humidity": safe_float(row.get("humidity")),
                "soil_moisture": safe_float(row.get("soil_moisture")),
                "ph": safe_float(row.get("ph")),
                "rainfall": safe_float(row.get("rainfall")),
                "nitrogen": safe_float(row.get("n")),
                "phosphorus": safe_float(row.get("p")),
                "potassium": safe_float(row.get("k"))
            })
except Exception as e:
    print(f"ERROR reading data file: {e}")
    sys.exit(1)

# --- Analysis ---
alerts = []
for i, r in enumerate(rows):
    if r["sfi"] < SFI_THRESHOLD:
        alerts.append({
            "row_index": i,
            "sfi": r["sfi"],
            "label": r["label"],
            "temperature": r["temperature"],
            "humidity": r["humidity"],
            "soil_moisture": r["soil_moisture"],
            "ph": r["ph"],
            "rainfall": r["rainfall"],
            "nitrogen": r["nitrogen"],
            "phosphorus": r["phosphorus"],
            "potassium": r["potassium"]
        })

# --- Summary ---
total_rows = len(rows) + missing_count
result_summary = [
    f"Total rows processed: {total_rows}",
    f"Rows with valid SFI: {len(rows)}",
    f"Rows with missing/invalid SFI: {missing_count}",
    f"Alert threshold: {SFI_THRESHOLD}",
    f"Alerts triggered: {len(alerts)}",
    f"Alert rate: {len(alerts)/len(rows)*100:.1f}%" if len(rows) > 0 else "N/A"
]

if alerts:
    avg_alert_sfi = sum(a["sfi"] for a in alerts) / len(alerts)
    result_summary.append(f"Average SFI in alerts: {avg_alert_sfi:.3f}")
    result_summary.append(f"Min SFI in alerts: {min(a['sfi'] for a in alerts):.3f}")
    result_summary.append(f"Max SFI in alerts: {max(a['sfi'] for a in alerts):.3f}")

# --- Output ---
result = {
    "task_name": "Soil Fertility Index Alert",
    "description": "Monitor the Soil Fertility Index (SFI) and trigger an alert if it falls below a predefined threshold (e.g., 0.7), indicating potential nutrient deficiency requiring soil amendment.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now(timezone.utc).isoformat(),
    "alerts": alerts
}

try:
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Results saved to: {output_file}")
    for line in result_summary:
        print(line)
except Exception as e:
    print(f"ERROR writing output: {e}")
    sys.exit(1)