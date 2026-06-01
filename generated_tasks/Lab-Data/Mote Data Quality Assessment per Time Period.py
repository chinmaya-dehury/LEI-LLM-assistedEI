"""
Task: Mote Data Quality Assessment per Time Period
Description: Assess the data quality of individual sensor motes across different time periods to identify potential issues with missing or truncated data.
"""

import csv
import json
import os
from datetime import datetime

def assess_mote_data_quality(file_path):
    mote_data_quality = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            mote_id = row['moteid']
            timestamp = f"{row['date']} {row['time']}"
            if mote_id not in mote_data_quality:
                mote_data_quality[mote_id] = {'total_readings': 0, 'missing_readings': 0, 'timestamps': []}
            mote_data_quality[mote_id]['total_readings'] += 1
            mote_data_quality[mote_id]['timestamps'].append(timestamp)
    for mote_id, data in mote_data_quality.items():
        sorted_timestamps = sorted(data['timestamps'])
        for i in range(1, len(sorted_timestamps)):
            prev_timestamp = datetime.strptime(sorted_timestamps[i-1], '%Y-%m-%d %H:%M:%S.%f')
            curr_timestamp = datetime.strptime(sorted_timestamps[i], '%Y-%m-%d %H:%M:%S.%f')
            time_diff = (curr_timestamp - prev_timestamp).total_seconds()
            if time_diff > 1:  # Assuming 1 second gap as missing reading
                mote_data_quality[mote_id]['missing_readings'] += (time_diff - 1)
    return mote_data_quality

def main():
    data_dir = 'data/Lab-Data'
    file_path = os.path.join(data_dir, 'raw_data.csv')
    mote_data_quality = assess_mote_data_quality(file_path)
    output_dir = 'output/Lab-Data'
    output_file_path = os.path.join(output_dir, 'Mote_Data_Quality_Assessment_result.json')
    with open(output_file_path, 'w') as output_file:
        json.dump(mote_data_quality, output_file, indent=4)

if __name__ == '__main__':
    main()