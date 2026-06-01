"""
Task: Epoch Sequence Gap Detection
Description: Detect gaps in epoch sequences to identify missing readings and ensure data synchronization across sensor motes.
"""

import csv
import json
import os
from pathlib import Path

def detect_epoch_gaps(file_path):
    epochs = set()
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                epoch = int(row['epoch'])
                epochs.add(epoch)
            except (ValueError, KeyError):
                continue
    sorted_epochs = sorted(epochs)
    gaps = []
    for i in range(len(sorted_epochs) - 1):
        if sorted_epochs[i + 1] - sorted_epochs[i] > 1:
            gaps.append((sorted_epochs[i], sorted_epochs[i + 1] - 1))
    return gaps

def main():
    data_dir = 'data/Lab-Data'
    file_path = os.path.join(data_dir, 'raw_data.csv')
    gaps = detect_epoch_gaps(file_path)
    result = {
        "task_name": "Epoch Sequence Gap Detection",
        "description": "Detect gaps in epoch sequences to identify missing readings and ensure data synchronization across sensor motes.",
        "result_summary": gaps,
        "result_generated_at": "2023-12-01"
    }
    output_dir = 'output/Lab-Data'
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(os.path.join(output_dir, 'Epoch Sequence Gap Detection_result.json'), 'w') as f:
        json.dump(result, f)

if __name__ == '__main__':
    main()