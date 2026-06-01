"""
Task: Identify Daily Patterns in Sensor Readings
Description: Analyze sensor readings (e.g., PT08.S1(CO), PT08.S5(O3)) for daily patterns or cycles, potentially aiding in anomaly detection or sensor calibration.
"""

import csv
import json
import os
from datetime import datetime

def load_data(file_path):
    data = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            data.append(row)
    return data

def extract_time_features(data):
    for row in data:
        dt = datetime.strptime(f'{row['Date']} {row['Time']}', '%d-%m-%Y %H:%M:%S')
        row['hour'] = dt.hour
    return data

def analyze_daily_patterns(data, sensor_cols):
    daily_avg = {}
    for row in data:
        hour = row['hour']
        for col in sensor_cols:
            if hour not in daily_avg:
                daily_avg[hour] = {}
            if col not in daily_avg[hour]:
                daily_avg[hour][col] = []
            daily_avg[hour][col].append(float(row[col]))
    for hour, cols in daily_avg.items():
        for col, values in cols.items():
            daily_avg[hour][col] = sum(values) / len(values)
    return daily_avg

def main():
    data_type = 'air_quality'
    file_path = os.path.join('data', data_type, 'raw_data.csv')
    data = load_data(file_path)
    data = extract_time_features(data)
    sensor_cols = ['PT08.S1(CO)', 'PT08.S5(O3)']
    daily_patterns = analyze_daily_patterns(data, sensor_cols)
    output_path = os.path.join('output', data_type, 'daily_patterns_result.json')
    with open(output_path, 'w') as file:
        json.dump({'daily_patterns': daily_patterns}, file)

if __name__ == '__main__':
    main()