"""
Task: Temperature Trend Analysis
Description: Analyze temperature trends across different motes and time periods to identify patterns and anomalies.
"""

import csv
import json
import os
from datetime import datetime

def analyze_temperature_trend(data_file):
    temperatures = {}
    with open(data_file, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            moteid = row['moteid']
            temperature = float(row['temperature'])
            if moteid not in temperatures:
                temperatures[moteid] = []
            temperatures[moteid].append(temperature)

    trend_summary = {}
    for moteid, temps in temperatures.items():
        avg_temp = sum(temps) / len(temps)
        trend_summary[moteid] = avg_temp

    return trend_summary

def main():
    data_type = 'Lab-Data'
    data_file = os.path.join('data', data_type, 'raw_data.csv')
    trend_summary = analyze_temperature_trend(data_file)
    result_file = os.path.join('output', data_type, 'Temperature_Trend_Analysis_result.json')
    with open(result_file, 'w') as f:
        json.dump({
            'task_name': 'Temperature Trend Analysis',
            'description': 'Analyze temperature trends across different motes and time periods to identify patterns and anomalies.',
            'result_summary': trend_summary,
            'result_generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }, f)

if __name__ == '__main__':
    main()