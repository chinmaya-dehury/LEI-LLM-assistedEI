"""
Task: Assess Organic Matter Content
Description: Monitor the percentage of organic matter in the soil to evaluate soil health.
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
import csv
import json
from pathlib import Path

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
    print("Data file not found.")
    exit(1)

organic_matter_values = []
dropped_rows = 0

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        organic_matter = row.get('organic_matter', '').strip()
        if organic_matter in ['', 'na', 'n/a', 'None']:
            dropped_rows += 1
            continue
        try:
            organic_matter_values.append(float(organic_matter))
        except ValueError:
            print(f"Invalid organic matter value: {organic_matter}")
            dropped_rows += 1

result_summary = {
    "average_organic_matter": sum(organic_matter_values) / len(organic_matter_values) if organic_matter_values else 0,
    "total_dropped_rows": dropped_rows
}

output_path = Path("/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run2") / "assess_organic_matter_content_result.json"
result = {
    "task_name": "Assess Organic Matter Content",
    "description": "Monitor the percentage of organic matter in the soil to evaluate soil health.",
    "result_summary": result_summary,
    "result_generated_at": "2023-10-01T12:00:00Z"
}

with open(output_path, 'w') as outfile:
    json.dump(result, outfile)
print(f"Results saved to {output_path}")