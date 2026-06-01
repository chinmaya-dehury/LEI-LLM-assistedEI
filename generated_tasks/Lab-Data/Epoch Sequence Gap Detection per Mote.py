"""
Task: Epoch Sequence Gap Detection per Mote
Description: Detect gaps in epoch sequences for each individual mote to identify missing readings and ensure data synchronization.
"""

import csv
import json
import os
from pathlib import Path

def detect_epoch_gaps(data_path, output_path):
    epoch_gaps = {}
    with open(data_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            moteid = int(row['moteid'])
            epoch = int(row['epoch'])
            if moteid not in epoch_gaps:
                epoch_gaps[moteid] = []
            if epoch_gaps[moteid] and epoch != epoch_gaps[moteid][-1] + 1:
                epoch_gaps[moteid].append((epoch_gaps[moteid][-1] + 1, epoch - 1))
            epoch_gaps[moteid].append(epoch)
    result = {
        'task_name': 'Epoch Sequence Gap Detection per Mote',
        'description': 'Detect gaps in epoch sequences for each individual mote to identify missing readings and ensure data synchronization.',
        'result_summary': [],
        'result_generated_at': ''
    }
    for moteid, epochs in epoch_gaps.items():
        gaps = []
        for i in range(1, len(epochs)):
            if epochs[i] != epochs[i-1] + 1:
                gaps.append((epochs[i-1] + 1, epochs[i] - 1))
        if gaps:
            result['result_summary'].append({ 'moteid': moteid, 'gaps': gaps })
    with open(output_path, 'w') as file:
        json.dump(result, file, indent=2)

if __name__ == '__main__':
    data_dir = 'data/Lab-Data'
    output_dir = 'output/Lab-Data'
    data_path = os.path.join(data_dir, 'raw_data.csv')
    output_path = os.path.join(output_dir, 'Epoch Sequence Gap Detection per Mote_result.json')
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    detect_epoch_gaps(data_path, output_path)