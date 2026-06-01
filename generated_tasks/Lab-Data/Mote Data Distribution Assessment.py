"""
Task: Mote Data Distribution Assessment
Description: Assess the distribution of data from individual sensor motes to identify potential issues with data quality or sensor calibration.
"""

import csv
import json
import os
from collections import defaultdict

def assess_mote_data_distribution(data_file):
    mote_counts = defaultdict(int)
    with open(data_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            moteid = int(row['moteid'])
            mote_counts[moteid] += 1
    return mote_counts

def main():
    data_dir = 'data/Lab-Data'
    data_file = os.path.join(data_dir, 'raw_data.csv')
    mote_counts = assess_mote_data_distribution(data_file)
    result = {
        'task_name': 'Mote Data Distribution Assessment',
        'description': 'Assess the distribution of data from individual sensor motes to identify potential issues with data quality or sensor calibration.',
        'result_summary': list(mote_counts.items()),
        'result_generated_at': ''
    }
    output_dir = 'output/Lab-Data'
    output_file = os.path.join(output_dir, 'Mote_Data_Distribution_Assessment_result.json')
    with open(output_file, 'w') as f:
        json.dump(result, f)
if __name__ == '__main__':
    main()