"""
Task: Mote Data Quality Assessment
Description: Assess the data quality of individual sensor motes to identify potential issues with missing or truncated data.
"""

import csv
import json
import os
from pathlib import Path

def assess_mote_data_quality(data_path):
    mote_data_quality = {}\n    with open(data_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            mote_id = row['moteid']
            if mote_id not in mote_data_quality:
                mote_data_quality[mote_id] = {'total_readings': 0, 'missing_values': 0}
            mote_data_quality[mote_id]['total_readings'] += 1
            if not all([row['temperature'], row['humidity'], row['light'], row['voltage']]):
                mote_data_quality[mote_id]['missing_values'] += 1
    return mote_data_quality

def save_result(result, output_path):
    with open(output_path, 'w') as file:
        json.dump(result, file)

if __name__ == '__main__':
    data_path = os.path.join('data', 'Lab-Data', 'raw_data.csv')
    result = assess_mote_data_quality(data_path)
    output_path = os.path.join('output', 'Lab-Data', 'Mote Data Quality Assessment_result.json')
    save_result(result, output_path)