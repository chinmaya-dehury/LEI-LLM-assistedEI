import re
"""
Task: Low Photosynthesis Potential Flag
Description: Assesses the Photosynthesis Potential (PP) index and marks data points with values below a set threshold as suboptimal for crop growth, enabling proactive environmental adjustments.
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
from datetime import datetime

# Resolve input file path dynamically
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

# Output path (CRITICAL: use specified path)
output_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_nvidia_nemotron-3-ultra-550b-a55b_run1")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "Low Photosynthesis Potential Flag_result.json"

# Threshold for suboptimal PP (based on data range ~0.6-1.1)
PP_THRESHOLD = 1.0

# Missing value placeholders
MISSING_VALUES = {'', 'na', 'n/a', 'None', 'none', '-'}

def safe_float(value):
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    val_str = str(value).strip().lower()
    if val_str in MISSING_VALUES:
        return None
    try:
        return float(val_str)
    except (ValueError, TypeError):
        return None

# Read and process data
flagged_records = []
total_records = 0
valid_pp_count = 0
low_pp_count = 0
dropped_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            total_records += 1

            # Check if 'pp' column exists
            if 'pp' not in row:
                dropped_rows += 1
                continue

            pp_value = safe_float(row.get('pp'))

            if pp_value is None:
                dropped_rows += 1
                continue

            valid_pp_count += 1

            # Flag if below threshold
            is_suboptimal = pp_value < PP_THRESHOLD
            if is_suboptimal:
                low_pp_count += 1
                record = {
                    'pp_value': round(pp_value, 4),
                    'is_suboptimal': True,
                    'threshold': PP_THRESHOLD
                }
                # Include key identifying columns if available
                for col in ['label', 'temperature', 'humidity', 'soil_moisture']:
                    if col in row and row[col]:
                        record[col] = row[col].strip()
                flagged_records.append(record)

except Exception as e:
    print(f"ERROR: Failed to read data file: {e}", file=sys.stderr)
    sys.exit(1)

# Build result
result = {
    "task_name": "Low Photosynthesis Potential Flag",
    "description": "Assesses the Photosynthesis Potential (PP) index and marks data points with values below a set threshold as suboptimal for crop growth, enabling proactive environmental adjustments.",
    "result_summary": [
        f"Total records processed: {total_records}",
        f"Records with valid PP: {valid_pp_count}",
        f"Records dropped (missing/invalid PP): {dropped_rows}",
        f"PP threshold for suboptimal flag: {PP_THRESHOLD}",
        f"Flagged records (PP < {PP_THRESHOLD}): {low_pp_count}",
        f"Flagged percentage: {round(low_pp_count / valid_pp_count * 100, 2) if valid_pp_count > 0 else 0}%"
    ],
    "flagged_records": flagged_records,
    "result_generated_at": datetime.now().isoformat()
}

# Save result
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"Result saved to: {output_file}")
    print(f"Flagged {low_pp_count} out of {valid_pp_count} valid records as suboptimal (PP < {PP_THRESHOLD})")
except Exception as e:
    print(f"ERROR: Failed to save result: {e}", file=sys.stderr)
    sys.exit(1)