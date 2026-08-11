import re
"""
Task: Nutrient Balance Ratio Validator
Description: Verifies if the Nutrient Balance Ratio (NBR) falls within an optimal range to prevent fertilizer waste and maintain soil chemistry.
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
    print("ERROR: Input data file not found.")
    sys.exit(1)

# Optimal NBR range for balanced soil chemistry
NBR_OPTIMAL_MIN = 15.0
NBR_OPTIMAL_MAX = 25.0

# Output directory
output_dir = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_qwen_qwen3.7-flash_anthropic_claude-3-haiku_run1")
output_dir.mkdir(parents=True, exist_ok=True)

def safe_float(value):
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    value = str(value).strip()
    if value in ('', 'NA', 'N/A', 'None', 'None'):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None

# Read and process data
nbr_values = []
invalid_count = 0
total_count = 0

try:
    with open(data_file, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys to lowercase
            row = {k.lower(): v for k, v in row.items()}
            total_count += 1
            
            nbr = safe_float(row.get('nbr'))
            if nbr is not None:
                nbr_values.append(nbr)
            else:
                invalid_count += 1
except Exception as e:
    print(f"ERROR: Failed to read data file: {e}")
    sys.exit(1)

# Validate NBR values
if not nbr_values:
    print("WARNING: No valid NBR values found in dataset.")
    result = {
        "task_name": "Nutrient Balance Ratio Validator",
        "description": "Verifies if the Nutrient Balance Ratio (NBR) falls within an optimal range to prevent fertilizer waste and maintain soil chemistry.",
        "result_summary": [
            "No valid NBR data available for validation.",
            f"Total rows processed: {total_count}",
            f"Invalid/missing NBR entries: {invalid_count}"
        ],
        "result_generated_at": datetime.now().isoformat()
    }
else:
    # Categorize NBR values
    within_optimal = [v for v in nbr_values if NBR_OPTIMAL_MIN <= v <= NBR_OPTIMAL_MAX]
    below_optimal = [v for v in nbr_values if v < NBR_OPTIMAL_MIN]
    above_optimal = [v for v in nbr_values if v > NBR_OPTIMAL_MAX]
    
    # Calculate statistics
    min_nbr = min(nbr_values)
    max_nbr = max(nbr_values)
    avg_nbr = sum(nbr_values) / len(nbr_values)
    
    # Identify critical outliers (far from optimal range)
    critical_low = [v for v in nbr_values if v < NBR_OPTIMAL_MIN * 0.8]
    critical_high = [v for v in nbr_values if v > NBR_OPTIMAL_MAX * 1.2]
    
    result = {
        "task_name": "Nutrient Balance Ratio Validator",
        "description": "Verifies if the Nutrient Balance Ratio (NBR) falls within an optimal range to prevent fertilizer waste and maintain soil chemistry.",
        "result_summary": [
            f"Total NBR values analyzed: {len(nbr_values)}",
            f"Invalid/missing NBR entries: {invalid_count}",
            f"NBR optimal range: {NBR_OPTIMAL_MIN} - {NBR_OPTIMAL_MAX}",
            f"Within optimal range: {len(within_optimal)} ({100*len(within_optimal)/len(nbr_values):.1f}%)",
            f"Below optimal range: {len(below_optimal)} ({100*len(below_optimal)/len(nbr_values):.1f}%)",
            f"Above optimal range: {len(above_optimal)} ({100*len(above_optimal)/len(nbr_values):.1f}%)",
            f"Min NBR: {min_nbr:.2f}",
            f"Max NBR: {max_nbr:.2f}",
            f"Mean NBR: {avg_nbr:.2f}",
            f"Critical low NBR (<{NBR_OPTIMAL_MIN*0.8:.1f}): {len(critical_low)} entries",
            f"Critical high NBR (>{NBR_OPTIMAL_MAX*1.2:.1f}): {len(critical_high)} entries"
        ],
        "result_generated_at": datetime.now().isoformat()
    }

# Save result
output_path = output_dir / "Nutrient Balance Ratio Validator_result.json"
with open(output_path, 'w') as f:
    json.dump(result, f, indent=2)

print(f"Result saved to: {output_path}")
print(f"NBR validation complete: {len(nbr_values)} values analyzed")