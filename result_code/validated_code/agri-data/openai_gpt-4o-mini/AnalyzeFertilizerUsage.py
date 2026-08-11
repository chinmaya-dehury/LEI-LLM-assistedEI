"""
Task: AnalyzeFertilizerUsage
Description: Evaluate the amount of fertilizer used per hectare to optimize fertilizer application strategies.
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

# Resolve the input file path
curr_dir = Path(__file__).resolve().parent
root_dir = curr_dir
while root_dir.name and not (root_dir / 'data').exists():
    parent = root_dir.parent
    if parent == root_dir:
        break
    root_dir = parent

data_file = root_dir / 'data' / 'agri-data' / 'raw_data.csv'
if not data_file.exists():
    data_file = root_dir / 'data' / 'agri-data' / 'raw_data.txt'
if not data_file.exists():
    print('Data file not found. Exiting.'); exit(1)

fertilizer_usage = []
cleaned_rows = 0
missing_rows = 0

with open(data_file, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        row = {k.lower(): v for k, v in row.items()}
        try:
            n = float(row.get('n', '')) if row.get('n', '') not in ['', 'NA', 'N/A', 'None'] else None
            p = float(row.get('p', '')) if row.get('p', '') not in ['', 'NA', 'N/A', 'None'] else None
            k = float(row.get('k', '')) if row.get('k', '') not in ['', 'NA', 'N/A', 'None'] else None
            if n is not None and p is not None and k is not None:
                fertilizer_usage.append((n, p, k))
                cleaned_rows += 1
            else:
                missing_rows += 1
                print(f'Missing values in row: {row}')
        except ValueError as e:
            missing_rows += 1
            print(f'Value error in row: {row} - {e}')

# Calculate average fertilizer usage per hectare
if cleaned_rows > 0:
    avg_n = sum(x[0] for x in fertilizer_usage) / cleaned_rows
    avg_p = sum(x[1] for x in fertilizer_usage) / cleaned_rows
    avg_k = sum(x[2] for x in fertilizer_usage) / cleaned_rows
    result_summary = {
        'average_n': avg_n,
        'average_p': avg_p,
        'average_k': avg_k,
        'cleaned_rows': cleaned_rows,
        'missing_rows': missing_rows
    }
else:
    result_summary = {'error': 'No valid data to analyze', 'missing_rows': missing_rows}

# Save results
output_path = '/home/dcc/LEI-Models-Comparision/output/agri-data/agri-data_openai_gpt-4o-mini_google_gemini-3.1-flash-lite_run1'
output_file = os.path.join(output_path, 'AnalyzeFertilizerUsage_result.json')
with open(output_file, 'w') as outfile:
    json.dump({
        'task_name': 'AnalyzeFertilizerUsage',
        'description': 'Evaluate the amount of fertilizer used per hectare to optimize fertilizer application strategies.',
        'result_summary': result_summary,
        'result_generated_at': '2023-10-01'
    }, outfile)
print(f'Results saved to {output_file}')