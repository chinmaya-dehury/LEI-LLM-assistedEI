"""
Task: Comparative Analysis Across Motes
Description: Perform comparative analysis across multiple motes to calibrate and validate sensor readings.
"""

import csv
import json
import os
from pathlib import Path

# Load data
file_path = os.path.join('data', 'Lab-Data', 'raw_data.csv')
data = []
with open(file_path, 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        data.append(row)

# Group data by moteid
mote_data = {}
for row in data:
    moteid = row['moteid']
    if moteid not in mote_data:
        mote_data[moteid] = []
    mote_data[moteid].append(float(row['temperature']))

# Calculate mean temperature for each mote
mote_means = {}
for moteid, temps in mote_data.items():
    mote_means[moteid] = sum(temps) / len(temps)

# Find overall mean temperature
overall_mean = sum(mote_means.values()) / len(mote_means)

# Calculate deviation from overall mean for each mote
deviations = {}
for moteid, mean in mote_means.items():
    deviations[moteid] = mean - overall_mean

# Save results
result_file = os.path.join('output', 'Lab-Data', 'Comparative_Analysis_Across_Motes_result.json')
result_dir = Path(result_file).parent
if not result_dir.exists():
    result_dir.mkdir(parents=True, exist_ok=True)
with open(result_file, 'w') as f:
    json.dump({
        "task_name": "Comparative Analysis Across Motes",
        "description": "Perform comparative analysis across multiple motes to calibrate and validate sensor readings.",
        "result_summary": deviations,
        "result_generated_at": "2023-01-01"
    }, f)