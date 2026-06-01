"""
Task: Humidity Trend Analysis
Description: Analyze humidity trends across different motes and time periods to identify patterns and anomalies.
"""

import csv
import json
import os
from datetime import datetime

def analyze_humidity_trend(data_file):
    humidity_readings = {}
    with open(data_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            moteid = row['moteid']
            humidity = float(row['humidity'])
            if moteid not in humidity_readings:
                humidity_readings[moteid] = []
            humidity_readings[moteid].append(humidity)
    trend_summary = {}
    for moteid, readings in humidity_readings.items():
        avg_humidity = sum(readings) / len(readings)
        trend_summary[moteid] = avg_humidity
    return trend_summary

def main():
    data_type = 'Lab-Data'
    data_file = os.path.join('data', data_type, 'raw_data.csv')
    trend_summary = analyze_humidity_trend(data_file)
    output_file = os.path.join('output', data_type, 'Humidity_Trend_Analysis_result.json')
    with open(output_file, 'w') as file:
        json.dump({
            'task_name': 'Humidity Trend Analysis',
            'description': 'Analyze humidity trends across different motes and time periods to identify patterns and anomalies.',
            'result_summary': trend_summary,
            'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, file)

if __name__ == '__main__':
    main()