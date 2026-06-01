"""
Task: Epoch Sequence Analysis
Description: Analyze epoch sequences to identify missing or delayed readings and ensure data synchronization.
"""

import csv
import json
import os
from pathlib import Path

def analyze_epoch_sequence(file_path):
    try:
        with open(file_path, 'r') as file:
            reader = csv.DictReader(file)
            epochs = [int(row['epoch']) for row in reader]
            if len(epochs) == 0:
                return []
            expected_epochs = list(range(min(epochs), max(epochs) + 1))
            missing_epochs = [epoch for epoch in expected_epochs if epoch not in epochs]
            return missing_epochs
    except Exception as e:
        print(f"Error reading file: {e}")
        return []

def main():
    data_dir = 'data/Lab-Data'
    file_path = os.path.join(data_dir, 'raw_data.csv')
    missing_epochs = analyze_epoch_sequence(file_path)
    result = {
        "task_name": "Epoch Sequence Analysis",
        "description": "Analyze epoch sequences to identify missing or delayed readings and ensure data synchronization.",
        "result_summary": missing_epochs,
        "result_generated_at": "2023-01-01"
    }
    output_dir = 'output/Lab-Data'
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(os.path.join(output_dir, 'Epoch Sequence Analysis_result.json'), 'w') as f:
        json.dump(result, f)
if __name__ == '__main__':
    main()