"""
Task: Soil Fertility Status Check
Description: Classifies the Soil Fertility Index (SFI) into low, medium, or high categories to provide a quick snapshot of overall soil health.
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
    print("ERROR: Input data file not found.", file=sys.stderr)
    sys.exit(1)

# Output path
output_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run1")
output_dir.mkdir(parents=True, exist_ok=True)
output_file = output_dir / "Soil Fertility Status Check_result.json"

# Helper function for safe numeric conversion
def safe_float(value):
    if value is None:
        return None
    value = str(value).strip()
    if value == '' or value.upper() in ('NA', 'N/A', 'NULL', 'NONE'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# SFI classification thresholds
SFI_LOW_THRESHOLD = 0.70
SFI_MEDIUM_THRESHOLD = 0.80

def classify_sfi(sfi_value):
    if sfi_value is None:
        return None
    if sfi_value < SFI_LOW_THRESHOLD:
        return 'low'
    elif sfi_value < SFI_MEDIUM_THRESHOLD:
        return 'medium'
    else:
        return 'high'

# Read and process data
sfi_values = []
missing_count = 0
total_rows = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            
            if 'sfi' not in row:
                print("WARNING: 'sfi' column not found in data.", file=sys.stderr)
                break
            
            sfi_val = safe_float(row.get('sfi'))
            if sfi_val is None:
                missing_count += 1
                continue
            
            classification = classify_sfi(sfi_val)
            sfi_values.append({
                'sfi': sfi_val,
                'classification': classification
            })
except Exception as e:
    print(f"ERROR: Failed to read data file: {e}", file=sys.stderr)
    sys.exit(1)

# Calculate summary statistics
if sfi_values:
    classifications = [v['classification'] for v in sfi_values]
    low_count = classifications.count('low')
    medium_count = classifications.count('medium')
    high_count = classifications.count('high')
    
    sfi_numeric = [v['sfi'] for v in sfi_values]
    avg_sfi = sum(sfi_numeric) / len(sfi_numeric)
    min_sfi = min(sfi_numeric)
    max_sfi = max(sfi_numeric)
    
    result_summary = [
        f"Total valid SFI records: {len(sfi_values)}",
        f"Low fertility: {low_count} ({low_count/len(sfi_values)*100:.1f}%)",
        f"Medium fertility: {medium_count} ({medium_count/len(sfi_values)*100:.1f}%)",
        f"High fertility: {high_count} ({high_count/len(sfi_values)*100:.1f}%)",
        f"Average SFI: {avg_sfi:.4f}",
        f"Min SFI: {min_sfi:.4f}",
        f"Max SFI: {max_sfi:.4f}",
        f"Missing/invalid SFI values: {missing_count}"
    ]
else:
    result_summary = ["No valid SFI data found."]

# Build result
result = {
    "task_name": "Soil Fertility Status Check",
    "description": "Classifies the Soil Fertility Index (SFI) into low, medium, or high categories to provide a quick snapshot of overall soil health.",
    "result_summary": result_summary,
    "result_generated_at": datetime.now().isoformat()
}

# Save result
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2)
    print(f"Result saved to: {output_file}")
except Exception as e:
    print(f"ERROR: Failed to save result: {e}", file=sys.stderr)
    sys.exit(1)

# Print summary to stdout
for line in result_summary:
    print(line)