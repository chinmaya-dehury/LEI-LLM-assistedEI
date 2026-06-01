"""
Task: Light Level Distribution Analysis
Description: Analyze the distribution of light level readings across different motes and time periods to identify patterns and potential issues with sensor calibration or environmental changes.
"""

import csv
import json
import os
import statistics
from pathlib import Path

def analyze_light_distribution(file_path):
    light_readings = []
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                light_reading = float(row['light'])
                light_readings.append(light_reading)
            except (ValueError, KeyError):
                pass
    if light_readings:
        summary = {
            'mean': statistics.mean(light_readings),
            'median': statistics.median(light_readings),
            'std_dev': statistics.stdev(light_readings) if len(light_readings) > 1 else 0
        }
    else:
        summary = {}
    return summary

def main():
    data_dir = 'data/Lab-Data'
    file_path = os.path.join(data_dir, 'raw_data.csv')
    result = analyze_light_distribution(file_path)
    output_dir = 'output/Lab-Data'
    output_path = os.path.join(output_dir, 'Light_Level_Distribution_Analysis_result.json')
    with open(output_path, 'w') as output_file:
        json.dump({
            'task_name': 'Light Level Distribution Analysis',
            'description': 'Analyze the distribution of light level readings across different motes and time periods to identify patterns and potential issues with sensor calibration or environmental changes.',
            'result_summary': result,
            'result_generated_at': ''
        }, output_file)

if __name__ == '__main__':
    main()